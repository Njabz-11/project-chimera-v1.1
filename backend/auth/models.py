"""
Authentication models for Project Chimera Enterprise
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    CLIENT = "client"
    AGENT = "agent"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.CLIENT
    status: UserStatus = UserStatus.ACTIVE
    is_active: bool = True


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    def validate_passwords_match(self):
        """Validate that passwords match"""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return True


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """User model as stored in database"""
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """User response model (without sensitive data)"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    scopes: List[str] = []


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    def validate_passwords_match(self):
        """Validate that new passwords match"""
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")
        return True


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    def validate_passwords_match(self):
        """Validate that passwords match"""
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return True


class APIKeyCreate(BaseModel):
    """API key creation model"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: List[str] = []
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API key response model"""
    id: int
    name: str
    description: Optional[str] = None
    key_preview: str  # Only first 8 characters
    scopes: List[str] = []
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    user_id: int
    username: str
    role: str
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
