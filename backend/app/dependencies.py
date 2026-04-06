"""
FastAPI dependencies: authentication, database sessions.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.auth_service import decode_access_token, get_user_by_id
from app.exceptions import AuthenticationError, AuthorizationError

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate the current user from JWT token."""
    if not credentials:
        raise AuthenticationError("Authentication required. Please provide a Bearer token.")

    payload = decode_access_token(credentials.credentials)
    user_id = int(payload.get("sub", 0))
    if not user_id:
        raise AuthenticationError("Invalid token payload.")

    user = await get_user_by_id(db, user_id)
    return user


def require_role(roles: list[str]):
    """Flexible RBAC: require any of the specified roles."""
    async def role_checker(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        db: AsyncSession = Depends(get_db),
    ):
        if not credentials:
            raise AuthenticationError("Authentication required.")
            
        payload = decode_access_token(credentials.credentials)
        user_role = payload.get("role")
        
        if user_role not in roles:
            # Allow "admin" role to bypass all specific role requirements as a superuser
            if user_role != "admin":
                raise AuthorizationError(f"Access requires one of: {roles}")

        user_id = int(payload.get("sub", 0))
        return await get_user_by_id(db, user_id)
        
    return role_checker


# Legacy dependency mapping for backward compatibility if needed in some places
require_admin = require_role(["admin"])


async def validate_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Validate an API key passed in the X-API-Key header."""
    from app.services.api_key_service import verify_api_key
    
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise AuthenticationError("Missing X-API-Key header.", status_code=401)
        
    key_info = await verify_api_key(db, api_key)
    if not key_info:
        raise AuthenticationError("Invalid or expired API key.", status_code=401)
        
    return key_info
