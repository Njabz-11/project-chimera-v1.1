"""
Authentication routes for Project Chimera Enterprise
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from auth.models import (
    UserCreate, UserResponse, UserUpdate, LoginRequest, Token,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    APIKeyCreate, APIKeyResponse, UserRole
)
from auth.security import get_security_manager, SecurityManager
from auth.dependencies import (
    get_current_user, require_admin, require_client_or_admin,
    rate_limit, get_current_user_token
)
from database.db_manager import DatabaseManager
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    security_manager: SecurityManager = Depends(get_security_manager),
    _rate_limit: bool = Depends(rate_limit(max_requests=10, window_seconds=300))  # 10 registrations per 5 minutes
):
    """Register a new user"""
    try:
        # Get global db_manager
        import main
        db_manager = main.db_manager
        # Validate password strength
        password_validation = security_manager.validate_password_strength(user_data.password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet requirements",
                    "errors": password_validation["errors"]
                }
            )
        
        # Validate passwords match
        if not user_data.validate_passwords_match():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Check if user already exists
        existing_user = await db_manager.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        existing_email = await db_manager.get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = security_manager.get_password_hash(user_data.password)
        
        # Create user
        user_dict = user_data.dict(exclude={"password", "confirm_password"})
        user_dict["hashed_password"] = hashed_password
        
        user_id = await db_manager.create_user(user_dict)
        
        # Get created user
        created_user = await db_manager.get_user_by_id(user_id)
        
        logger.info(f"New user registered: {user_data.username}")
        
        return UserResponse(**created_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    request: Request,
    security_manager: SecurityManager = Depends(get_security_manager),
    _rate_limit: bool = Depends(rate_limit(max_requests=20, window_seconds=300))  # 20 login attempts per 5 minutes
):
    """Authenticate user and return JWT tokens"""
    try:
        # Get global db_manager
        import main
        db_manager = main.db_manager
        # Get user
        user = await db_manager.get_user_by_username(login_data.username)
        
        if not user:
            # Log failed attempt
            logger.warning(f"Login attempt with non-existent username: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if account is locked
        if user.get("locked_until") and datetime.utcnow() < user["locked_until"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is temporarily locked due to failed login attempts"
            )
        
        # Verify password
        if not security_manager.verify_password(login_data.password, user["hashed_password"]):
            # Increment failed attempts
            await db_manager.increment_failed_login_attempts(user["id"])
            
            logger.warning(f"Failed login attempt for user: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Reset failed attempts on successful login
        await db_manager.reset_failed_login_attempts(user["id"])
        
        # Update last login
        await db_manager.update_last_login(user["id"])
        
        # Create tokens
        token_data = {
            "sub": user["username"],
            "user_id": user["id"],
            "role": user["role"],
            "scopes": ["read", "write"]  # Default scopes
        }
        
        access_token_expires = timedelta(minutes=security_manager.settings.access_token_expire_minutes)
        if login_data.remember_me:
            access_token_expires = timedelta(days=7)  # Extended for remember me
        
        access_token = security_manager.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        refresh_token = security_manager.create_refresh_token(data=token_data)
        
        logger.info(f"Successful login for user: {login_data.username}")
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    security_manager: SecurityManager = Depends(get_security_manager)
):
    """Refresh access token using refresh token"""
    try:
        # Get global db_manager
        import main
        db_manager = main.db_manager
        # Verify refresh token
        payload = security_manager.verify_token(refresh_token, "refresh")
        
        # Get user
        user_id = payload.get("user_id")
        user = await db_manager.get_user_by_id(user_id)
        
        if not user or not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new tokens
        token_data = {
            "sub": user["username"],
            "user_id": user["id"],
            "role": user["role"],
            "scopes": payload.get("scopes", ["read", "write"])
        }
        
        access_token = security_manager.create_access_token(data=token_data)
        new_refresh_token = security_manager.create_refresh_token(data=token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=security_manager.settings.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user)
):
    """Logout user (in production, would invalidate tokens)"""
    logger.info(f"User logged out: {current_user['username']}")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(**current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update current user information"""
    try:
        # Get global db_manager
        import main
        db_manager = main.db_manager
        # Update user
        updated_user = await db_manager.update_user(current_user["id"], user_update.dict(exclude_unset=True))
        
        logger.info(f"User updated profile: {current_user['username']}")
        
        return UserResponse(**updated_user)
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    security_manager: SecurityManager = Depends(get_security_manager)
):
    """Change user password"""
    try:
        # Get global db_manager
        import main
        db_manager = main.db_manager
        # Validate passwords match
        if not password_change.validate_passwords_match():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match"
            )
        
        # Verify current password
        if not security_manager.verify_password(
            password_change.current_password, 
            current_user["hashed_password"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password strength
        password_validation = security_manager.validate_password_strength(password_change.new_password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "New password does not meet requirements",
                    "errors": password_validation["errors"]
                }
            )
        
        # Hash new password
        new_hashed_password = security_manager.get_password_hash(password_change.new_password)
        
        # Update password
        await db_manager.update_user_password(current_user["id"], new_hashed_password)
        
        logger.info(f"Password changed for user: {current_user['username']}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )
