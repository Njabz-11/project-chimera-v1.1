"""
Multi-tenant models for Project Chimera Enterprise
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class TenantStatus(str, Enum):
    """Tenant status options"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TenantPlan(str, Enum):
    """Tenant subscription plans"""
    TRIAL = "trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class TenantBase(BaseModel):
    """Base tenant model"""
    name: str = Field(..., min_length=2, max_length=100)
    domain: str = Field(..., min_length=3, max_length=100)
    status: TenantStatus = TenantStatus.TRIAL
    plan: TenantPlan = TenantPlan.TRIAL
    max_users: int = Field(default=5, ge=1, le=1000)
    max_missions: int = Field(default=10, ge=1, le=10000)
    max_leads: int = Field(default=1000, ge=1, le=100000)
    settings: Dict[str, Any] = Field(default_factory=dict)


class TenantCreate(TenantBase):
    """Tenant creation model"""
    admin_username: str = Field(..., min_length=3, max_length=50)
    admin_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    admin_password: str = Field(..., min_length=8, max_length=100)
    admin_full_name: Optional[str] = None

    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain format"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Domain must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()


class TenantUpdate(BaseModel):
    """Tenant update model"""
    name: Optional[str] = None
    status: Optional[TenantStatus] = None
    plan: Optional[TenantPlan] = None
    max_users: Optional[int] = None
    max_missions: Optional[int] = None
    max_leads: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None


class TenantInDB(TenantBase):
    """Tenant model as stored in database"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    usage_stats: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class TenantResponse(TenantBase):
    """Tenant response model"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    current_users: int = 0
    current_missions: int = 0
    current_leads: int = 0

    class Config:
        from_attributes = True


class TenantUsage(BaseModel):
    """Tenant usage statistics"""
    tenant_id: int
    users_count: int
    missions_count: int
    leads_count: int
    conversations_count: int
    api_calls_count: int
    storage_used_mb: float
    bandwidth_used_mb: float
    last_updated: datetime


class TenantLimits(BaseModel):
    """Tenant resource limits"""
    max_users: int
    max_missions: int
    max_leads: int
    max_api_calls_per_hour: int
    max_storage_mb: int
    max_bandwidth_mb_per_day: int
    features_enabled: List[str]


class TenantContext(BaseModel):
    """Tenant context for request processing"""
    tenant_id: int
    tenant_domain: str
    tenant_name: str
    tenant_status: TenantStatus
    tenant_plan: TenantPlan
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    limits: Optional[TenantLimits] = None


class TenantInvitation(BaseModel):
    """Tenant user invitation"""
    tenant_id: int
    email: str
    role: str = "client"
    invited_by: int
    expires_at: datetime
    accepted: bool = False


class TenantAuditLog(BaseModel):
    """Tenant audit log entry"""
    tenant_id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime


class TenantBilling(BaseModel):
    """Tenant billing information"""
    tenant_id: int
    plan: TenantPlan
    billing_cycle: str  # monthly, yearly
    amount: float
    currency: str = "USD"
    next_billing_date: datetime
    payment_method: Optional[str]
    billing_address: Optional[Dict[str, str]]


class TenantFeature(BaseModel):
    """Tenant feature configuration"""
    tenant_id: int
    feature_name: str
    enabled: bool
    configuration: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class TenantMetrics(BaseModel):
    """Tenant performance metrics"""
    tenant_id: int
    metric_name: str
    metric_value: float
    metric_type: str  # counter, gauge, histogram
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime


class TenantBackup(BaseModel):
    """Tenant data backup information"""
    tenant_id: int
    backup_type: str  # full, incremental
    status: str  # pending, running, completed, failed
    file_path: Optional[str]
    size_mb: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
