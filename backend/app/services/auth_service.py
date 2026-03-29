"""
Authentication service: JWT tokens, password hashing, user management.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import User, AuditLog, AnalysisRecord
from app.exceptions import AuthenticationError, ResourceNotFoundError


settings = get_settings()

# ── Password Hashing ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ── JWT Tokens ────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired.")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token.")


# ── User CRUD ─────────────────────────────────────────────────────

async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    organization: Optional[str] = None,
    role: str = "analyst",
) -> User:
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise AuthenticationError("A user with this email already exists.")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        organization=organization,
        role=role,
    )
    db.add(user)
    await db.flush()  # get the ID without committing
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials and return user."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("Account is disabled.")

    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ResourceNotFoundError("User")
    return user


async def get_user_analysis_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(AnalysisRecord.id)).where(AnalysisRecord.user_id == user_id)
    )
    return result.scalar() or 0


# ── Audit Logging ─────────────────────────────────────────────────

async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    resource: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Write an audit log entry."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
