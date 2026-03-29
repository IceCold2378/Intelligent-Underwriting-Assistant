"""
Authentication router: register, login, user profile.
"""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user
from app.models.database import get_db, User
from app.models.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfile,
)
from app.services.auth_service import (
    create_user,
    authenticate_user,
    create_access_token,
    get_user_analysis_count,
    log_audit,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    user = await create_user(
        db=db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        organization=body.organization,
    )
    token = create_access_token(user.id, user.email, user.role)

    await log_audit(
        db=db,
        action="register",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    logger.info("New user registered: %s (id=%d)", user.email, user.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Log in and receive a JWT access token."""
    user = await authenticate_user(db, body.email, body.password)
    token = create_access_token(user.id, user.email, user.role)

    await log_audit(
        db=db,
        action="login",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    logger.info("User logged in: %s", user.email)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    count = await get_user_analysis_count(db, current_user.id)
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        organization=current_user.organization,
        role=current_user.role,
        created_at=current_user.created_at,
        analysis_count=count,
    )
