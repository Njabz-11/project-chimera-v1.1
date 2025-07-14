"""
Tenant management for Project Chimera Enterprise
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from tenants.models import (
    TenantCreate, TenantUpdate, TenantInDB, TenantUsage, 
    TenantLimits, TenantPlan, TenantStatus
)
from database.db_manager import DatabaseManager
from auth.security import get_security_manager
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)


class TenantManager:
    """Manages multi-tenant operations"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.security_manager = get_security_manager()

    async def create_tenant(self, tenant_data: TenantCreate) -> Dict[str, Any]:
        """Create a new tenant with admin user"""
        try:
            # Check if domain is available
            existing_tenant = await self.get_tenant_by_domain(tenant_data.domain)
            if existing_tenant:
                raise ValueError(f"Domain '{tenant_data.domain}' is already taken")

            # Create tenant
            tenant_dict = tenant_data.dict(exclude={"admin_username", "admin_email", "admin_password", "admin_full_name"})
            tenant_dict["created_at"] = datetime.utcnow()
            
            # Set trial expiration
            if tenant_dict["plan"] == TenantPlan.TRIAL:
                tenant_dict["expires_at"] = datetime.utcnow() + timedelta(days=14)

            tenant_id = await self.db_manager.create_tenant(tenant_dict)

            # Create admin user for tenant
            admin_user_data = {
                "username": tenant_data.admin_username,
                "email": tenant_data.admin_email,
                "full_name": tenant_data.admin_full_name,
                "hashed_password": self.security_manager.get_password_hash(tenant_data.admin_password),
                "role": "admin",
                "status": "active",
                "is_active": True,
                "tenant_id": tenant_id
            }

            admin_user_id = await self.db_manager.create_user(admin_user_data)

            # Initialize tenant usage
            await self._initialize_tenant_usage(tenant_id)

            # Log tenant creation
            logger.info(f"New tenant created: {tenant_data.domain} (ID: {tenant_id})")

            return {
                "tenant_id": tenant_id,
                "admin_user_id": admin_user_id,
                "domain": tenant_data.domain,
                "status": "created"
            }

        except Exception as e:
            logger.error(f"Failed to create tenant: {e}")
            raise

    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Get tenant by ID"""
        try:
            cursor = await self.db_manager.connection.execute(
                "SELECT * FROM tenants WHERE id = ?", (tenant_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get tenant by ID: {e}")
            return None

    async def get_tenant_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get tenant by domain"""
        try:
            cursor = await self.db_manager.connection.execute(
                "SELECT * FROM tenants WHERE domain = ?", (domain.lower(),)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get tenant by domain: {e}")
            return None

    async def update_tenant(self, tenant_id: int, update_data: TenantUpdate) -> Optional[Dict[str, Any]]:
        """Update tenant information"""
        try:
            set_clauses = []
            params = []
            
            update_dict = update_data.dict(exclude_unset=True)
            
            for field, value in update_dict.items():
                if field in ["name", "status", "plan", "max_users", "max_missions", "max_leads", "settings"]:
                    set_clauses.append(f"{field} = ?")
                    params.append(value)
            
            if set_clauses:
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(tenant_id)
                
                query = f"UPDATE tenants SET {', '.join(set_clauses)} WHERE id = ?"
                await self.db_manager.connection.execute(query, params)
                await self.db_manager.connection.commit()
            
            return await self.get_tenant_by_id(tenant_id)
        except Exception as e:
            logger.error(f"Failed to update tenant: {e}")
            raise

    async def get_all_tenants(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all tenants with pagination"""
        try:
            cursor = await self.db_manager.connection.execute(
                "SELECT * FROM tenants ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, skip)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all tenants: {e}")
            return []

    async def get_tenant_usage(self, tenant_id: int) -> TenantUsage:
        """Get current tenant usage statistics"""
        try:
            # Get user count
            cursor = await self.db_manager.connection.execute(
                "SELECT COUNT(*) as count FROM users WHERE tenant_id = ?", (tenant_id,)
            )
            users_count = (await cursor.fetchone())["count"]

            # Get mission count
            cursor = await self.db_manager.connection.execute(
                "SELECT COUNT(*) as count FROM mission_briefings WHERE tenant_id = ?", (tenant_id,)
            )
            missions_count = (await cursor.fetchone())["count"]

            # Get leads count
            cursor = await self.db_manager.connection.execute(
                """SELECT COUNT(*) as count FROM leads l 
                   JOIN mission_briefings m ON l.mission_id = m.id 
                   WHERE m.tenant_id = ?""", (tenant_id,)
            )
            leads_count = (await cursor.fetchone())["count"]

            # Get conversations count
            cursor = await self.db_manager.connection.execute(
                """SELECT COUNT(*) as count FROM conversations c 
                   JOIN leads l ON c.lead_id = l.id 
                   JOIN mission_briefings m ON l.mission_id = m.id 
                   WHERE m.tenant_id = ?""", (tenant_id,)
            )
            conversations_count = (await cursor.fetchone())["count"]

            return TenantUsage(
                tenant_id=tenant_id,
                users_count=users_count,
                missions_count=missions_count,
                leads_count=leads_count,
                conversations_count=conversations_count,
                api_calls_count=0,  # TODO: Implement API call tracking
                storage_used_mb=0.0,  # TODO: Implement storage tracking
                bandwidth_used_mb=0.0,  # TODO: Implement bandwidth tracking
                last_updated=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Failed to get tenant usage: {e}")
            return TenantUsage(
                tenant_id=tenant_id,
                users_count=0,
                missions_count=0,
                leads_count=0,
                conversations_count=0,
                api_calls_count=0,
                storage_used_mb=0.0,
                bandwidth_used_mb=0.0,
                last_updated=datetime.utcnow()
            )

    async def get_tenant_limits(self, tenant_id: int) -> TenantLimits:
        """Get tenant resource limits based on plan"""
        try:
            tenant = await self.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")

            plan = tenant["plan"]
            
            # Define limits by plan
            plan_limits = {
                TenantPlan.TRIAL: TenantLimits(
                    max_users=2,
                    max_missions=5,
                    max_leads=100,
                    max_api_calls_per_hour=100,
                    max_storage_mb=100,
                    max_bandwidth_mb_per_day=1000,
                    features_enabled=["basic_agents", "email_integration"]
                ),
                TenantPlan.STARTER: TenantLimits(
                    max_users=5,
                    max_missions=25,
                    max_leads=1000,
                    max_api_calls_per_hour=500,
                    max_storage_mb=1000,
                    max_bandwidth_mb_per_day=5000,
                    features_enabled=["basic_agents", "email_integration", "content_generation"]
                ),
                TenantPlan.PROFESSIONAL: TenantLimits(
                    max_users=25,
                    max_missions=100,
                    max_leads=10000,
                    max_api_calls_per_hour=2000,
                    max_storage_mb=10000,
                    max_bandwidth_mb_per_day=25000,
                    features_enabled=["all_agents", "email_integration", "content_generation", "fulfillment", "analytics"]
                ),
                TenantPlan.ENTERPRISE: TenantLimits(
                    max_users=100,
                    max_missions=1000,
                    max_leads=100000,
                    max_api_calls_per_hour=10000,
                    max_storage_mb=100000,
                    max_bandwidth_mb_per_day=100000,
                    features_enabled=["all_agents", "email_integration", "content_generation", "fulfillment", "analytics", "custom_integrations", "priority_support"]
                )
            }

            # Override with custom limits if set
            custom_limits = plan_limits.get(plan, plan_limits[TenantPlan.TRIAL])
            
            if tenant.get("max_users"):
                custom_limits.max_users = tenant["max_users"]
            if tenant.get("max_missions"):
                custom_limits.max_missions = tenant["max_missions"]
            if tenant.get("max_leads"):
                custom_limits.max_leads = tenant["max_leads"]

            return custom_limits

        except Exception as e:
            logger.error(f"Failed to get tenant limits: {e}")
            return TenantLimits(
                max_users=1,
                max_missions=1,
                max_leads=10,
                max_api_calls_per_hour=10,
                max_storage_mb=10,
                max_bandwidth_mb_per_day=100,
                features_enabled=["basic_agents"]
            )

    async def update_tenant_activity(self, tenant_id: int, activity_data: Dict[str, Any]):
        """Update tenant last activity"""
        try:
            await self.db_manager.connection.execute(
                "UPDATE tenants SET last_activity = CURRENT_TIMESTAMP WHERE id = ?",
                (tenant_id,)
            )
            await self.db_manager.connection.commit()
        except Exception as e:
            logger.warning(f"Failed to update tenant activity: {e}")

    async def check_tenant_limits(self, tenant_id: int, resource_type: str, count: int = 1) -> bool:
        """Check if tenant can create more resources"""
        try:
            usage = await self.get_tenant_usage(tenant_id)
            limits = await self.get_tenant_limits(tenant_id)

            checks = {
                "users": usage.users_count + count <= limits.max_users,
                "missions": usage.missions_count + count <= limits.max_missions,
                "leads": usage.leads_count + count <= limits.max_leads,
            }

            return checks.get(resource_type, True)

        except Exception as e:
            logger.error(f"Failed to check tenant limits: {e}")
            return False

    async def _initialize_tenant_usage(self, tenant_id: int):
        """Initialize tenant usage tracking"""
        try:
            await self.db_manager.connection.execute(
                """INSERT INTO tenant_usage (
                    tenant_id, users_count, missions_count, leads_count, 
                    conversations_count, api_calls_count, storage_used_mb, 
                    bandwidth_used_mb, last_updated
                ) VALUES (?, 0, 0, 0, 0, 0, 0.0, 0.0, CURRENT_TIMESTAMP)""",
                (tenant_id,)
            )
            await self.db_manager.connection.commit()
        except Exception as e:
            logger.warning(f"Failed to initialize tenant usage: {e}")

    async def cleanup_expired_tenants(self):
        """Cleanup expired trial tenants"""
        try:
            # Get expired trial tenants
            cursor = await self.db_manager.connection.execute(
                """SELECT id, domain FROM tenants 
                   WHERE plan = 'trial' AND expires_at < CURRENT_TIMESTAMP AND status = 'active'"""
            )
            expired_tenants = await cursor.fetchall()

            for tenant in expired_tenants:
                # Update status to expired
                await self.db_manager.connection.execute(
                    "UPDATE tenants SET status = 'expired' WHERE id = ?",
                    (tenant["id"],)
                )
                
                logger.info(f"Tenant {tenant['domain']} (ID: {tenant['id']}) expired")

            await self.db_manager.connection.commit()
            
            return len(expired_tenants)

        except Exception as e:
            logger.error(f"Failed to cleanup expired tenants: {e}")
            return 0
