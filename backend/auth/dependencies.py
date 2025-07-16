"""
Authentication dependencies for FastAPI endpoints
"""
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from auth.security import get_security_manager, SecurityManager
from auth.models import TokenData, UserRole
from database.db_manager import DatabaseManager
from utils.logger import ChimeraLogger

logger = ChimeraLogger.get_logger(__name__)

def get_db_manager():
    """Get the global database manager instance from main module"""
    import main
    return main.db_manager

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    security_manager: SecurityManager = Depends(get_security_manager)
) -> TokenData:
    """Extract and validate current user from JWT token"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Verify token
        payload = security_manager.verify_token(credentials.credentials, "access")
        
        # Extract user data
        username = payload.get("sub")
        user_id = payload.get("user_id")
        role = payload.get("role")
        scopes = payload.get("scopes", [])
        
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            username=username,
            user_id=user_id,
            role=role,
            scopes=scopes
        )
        
        return token_data
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_token)
) -> dict:
    """Get current user from database"""

    # Get global db_manager
    import main
    db_manager = main.db_manager

    if not db_manager:
        # Fallback to basic user info from token
        return {
            "id": token_data.user_id,
            "username": token_data.username,
            "role": token_data.role
        }
    
    try:
        # Get user from database
        user = await db_manager.get_user_by_id(token_data.user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User service error"
        )


def require_roles(allowed_roles: List[UserRole]):
    """Dependency factory for role-based access control"""
    
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        
        if user_role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
            )
        
        return current_user
    
    return role_checker


def require_scopes(required_scopes: List[str]):
    """Dependency factory for scope-based access control"""
    
    def scope_checker(token_data: TokenData = Depends(get_current_user_token)) -> TokenData:
        user_scopes = set(token_data.scopes)
        required_scopes_set = set(required_scopes)
        
        if not required_scopes_set.issubset(user_scopes):
            missing_scopes = required_scopes_set - user_scopes
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Missing scopes: {list(missing_scopes)}"
            )
        
        return token_data
    
    return scope_checker


# Convenience dependencies for common roles
require_admin = require_roles([UserRole.ADMIN])
require_client_or_admin = require_roles([UserRole.CLIENT, UserRole.ADMIN])
require_agent_or_admin = require_roles([UserRole.AGENT, UserRole.ADMIN])


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    security_manager: SecurityManager = Depends(get_security_manager)
) -> Optional[dict]:
    """Get current user if authenticated, otherwise return None"""
    
    if not credentials:
        return None
    
    try:
        token_data = await get_current_user_token(credentials, security_manager)
        return await get_current_user(token_data)
    except HTTPException:
        return None
    except Exception:
        return None


async def validate_api_key(
    request: Request,
    security_manager: SecurityManager = Depends(get_security_manager)
) -> Optional[dict]:
    """Validate API key from headers"""
    
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        return None
    
    try:
        # In production, this would check against database
        # For now, return basic validation
        if len(api_key) >= 32:  # Basic length check
            return {"api_key": True, "type": "api_key"}
        return None
        
    except Exception as e:
        logger.error(f"API key validation error: {e}")
        return None


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """Rate limiting dependency"""
    
    def rate_limiter(
        request: Request,
        security_manager: SecurityManager = Depends(get_security_manager)
    ):
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit (simplified - in production use Redis)
        if not security_manager.check_rate_limit(client_ip, max_requests, window_seconds // 60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        return True
    
    return rate_limiter
