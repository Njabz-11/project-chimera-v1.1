"""
Multi-tenant middleware for Project Chimera Enterprise
Handles tenant detection and context setting
"""
import re
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from tenants.models import TenantContext, TenantStatus
from tenants.manager import TenantManager
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to handle multi-tenant requests"""

    def __init__(self, app, tenant_manager: TenantManager):
        super().__init__(app)
        self.tenant_manager = tenant_manager
        
        # Paths that don't require tenant context
        self.public_paths = [
            r'^/health$',
            r'^/docs.*',
            r'^/redoc.*',
            r'^/openapi\.json$',
            r'^/static/.*',
            r'^/metrics.*',
            r'^/admin/tenants.*',  # Tenant management endpoints
        ]
        
        # Compile regex patterns
        self.public_patterns = [re.compile(pattern) for pattern in self.public_paths]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant context"""
        
        # Skip tenant detection for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        try:
            # Detect tenant from request
            tenant_context = await self._detect_tenant(request)
            
            if not tenant_context:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": "Tenant not found or invalid",
                        "error_code": "TENANT_NOT_FOUND"
                    }
                )
            
            # Validate tenant status
            if tenant_context.tenant_status not in [TenantStatus.ACTIVE, TenantStatus.TRIAL]:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": f"Tenant is {tenant_context.tenant_status.value}",
                        "error_code": "TENANT_SUSPENDED"
                    }
                )
            
            # Add tenant context to request state
            request.state.tenant = tenant_context
            
            # Log tenant activity
            await self._log_tenant_activity(tenant_context, request)
            
            # Process request
            response = await call_next(request)
            
            # Add tenant headers to response
            response.headers["X-Tenant-ID"] = str(tenant_context.tenant_id)
            response.headers["X-Tenant-Domain"] = tenant_context.tenant_domain
            
            return response
            
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Tenant processing error",
                    "error_code": "TENANT_ERROR"
                }
            )

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (doesn't require tenant context)"""
        return any(pattern.match(path) for pattern in self.public_patterns)

    async def _detect_tenant(self, request: Request) -> Optional[TenantContext]:
        """Detect tenant from request"""
        
        # Method 1: Subdomain detection (preferred)
        tenant_domain = self._extract_subdomain(request)
        
        # Method 2: Header-based detection
        if not tenant_domain:
            tenant_domain = request.headers.get("X-Tenant-Domain")
        
        # Method 3: Query parameter (for development/testing)
        if not tenant_domain:
            tenant_domain = request.query_params.get("tenant")
        
        if not tenant_domain:
            return None
        
        # Get tenant from database
        tenant = await self.tenant_manager.get_tenant_by_domain(tenant_domain)
        
        if not tenant:
            return None
        
        # Get tenant limits
        limits = await self.tenant_manager.get_tenant_limits(tenant["id"])
        
        return TenantContext(
            tenant_id=tenant["id"],
            tenant_domain=tenant["domain"],
            tenant_name=tenant["name"],
            tenant_status=TenantStatus(tenant["status"]),
            tenant_plan=tenant["plan"],
            limits=limits
        )

    def _extract_subdomain(self, request: Request) -> Optional[str]:
        """Extract tenant subdomain from host header"""
        host = request.headers.get("host", "")
        
        # Remove port if present
        host = host.split(":")[0]
        
        # Split by dots
        parts = host.split(".")
        
        # If we have at least 3 parts (subdomain.domain.tld), extract subdomain
        if len(parts) >= 3:
            subdomain = parts[0]
            
            # Skip common subdomains
            if subdomain not in ["www", "api", "admin"]:
                return subdomain
        
        return None

    async def _log_tenant_activity(self, tenant_context: TenantContext, request: Request):
        """Log tenant activity for monitoring"""
        try:
            await self.tenant_manager.update_tenant_activity(
                tenant_context.tenant_id,
                {
                    "path": request.url.path,
                    "method": request.method,
                    "ip_address": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent")
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log tenant activity: {e}")


class TenantContextDependency:
    """Dependency to get tenant context from request"""
    
    def __call__(self, request: Request) -> TenantContext:
        """Get tenant context from request state"""
        if not hasattr(request.state, 'tenant'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context not found"
            )
        
        return request.state.tenant


class TenantResourceLimiter:
    """Middleware to enforce tenant resource limits"""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
    
    async def check_limits(self, tenant_context: TenantContext, resource_type: str, count: int = 1) -> bool:
        """Check if tenant can create more resources"""
        
        if not tenant_context.limits:
            return True
        
        current_usage = await self.tenant_manager.get_tenant_usage(tenant_context.tenant_id)
        
        limits_map = {
            "users": (current_usage.users_count, tenant_context.limits.max_users),
            "missions": (current_usage.missions_count, tenant_context.limits.max_missions),
            "leads": (current_usage.leads_count, tenant_context.limits.max_leads),
        }
        
        if resource_type in limits_map:
            current, limit = limits_map[resource_type]
            return (current + count) <= limit
        
        return True
    
    def require_limit_check(self, resource_type: str, count: int = 1):
        """Decorator to check resource limits"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract tenant context from request
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                if request and hasattr(request.state, 'tenant'):
                    tenant_context = request.state.tenant
                    
                    if not await self.check_limits(tenant_context, resource_type, count):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Tenant has reached the limit for {resource_type}",
                            headers={"X-Error-Code": "RESOURCE_LIMIT_EXCEEDED"}
                        )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator


# Global instances
get_tenant_context = TenantContextDependency()
