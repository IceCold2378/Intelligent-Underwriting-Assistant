"""
API key management service.

Handles generating, hashing, verifying, and listing API keys
for service-to-service authentication.
"""

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.database import ApiKey
from app.models.schemas import ApiKeyCreate


class KeyGenerationResult(TypedDict):
    id: int
    name: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    api_key: str  # The raw, plain-text key (only returned once)


def generate_raw_key() -> str:
    """Generate a high-entropy API key."""
    prefix = "sk_live_"
    entropy = secrets.token_urlsafe(32)
    return f"{prefix}{entropy}"


def hash_key(api_key: str) -> str:
    """Hash the API key for safe storage (SHA-256)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def create_api_key(db: AsyncSession, data: ApiKeyCreate, user_id: int) -> KeyGenerationResult:
    """Create a new API key and return the raw string (once only)."""
    raw_key = generate_raw_key()
    hashed_key = hash_key(raw_key)

    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    db_key = ApiKey(
        key_hash=hashed_key,
        name=data.name,
        scopes=",".join(data.scopes),
        user_id=user_id,
        expires_at=expires_at,
        is_active=1,
    )

    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)

    return {
        "id": db_key.id,
        "name": db_key.name,
        "scopes": db_key.scopes.split(","),
        "expires_at": db_key.expires_at,
        "created_at": db_key.created_at,
        "api_key": raw_key,  # Raw key returned only here
    }


async def verify_api_key(db: AsyncSession, target_key: str) -> dict | None:
    """Verify an API key exists, is active, and is not expired."""
    hashed = hash_key(target_key)

    stmt = select(ApiKey).where(
        ApiKey.key_hash == hashed,
        ApiKey.is_active == 1
    )
    result = await db.execute(stmt)
    db_key = result.scalar_one_or_none()

    if not db_key:
        return None

    # Check expiration
    if db_key.expires_at:
        # DB returns naive datetime, convert to UTC-aware if necessary
        expires_at = db_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if datetime.now(timezone.utc) > expires_at:
            return None

    return {
        "id": db_key.id,
        "name": db_key.name,
        "scopes": db_key.scopes.split(","),
        "user_id": db_key.user_id,
    }


async def list_api_keys(db: AsyncSession, user_id: int) -> list[dict]:
    """List all API keys for a user (without the raw keys)."""
    stmt = select(ApiKey).where(
        ApiKey.user_id == user_id,
        ApiKey.is_active == 1
    )
    result = await db.execute(stmt)
    keys = result.scalars().all()

    return [
        {
            "id": k.id,
            "name": k.name,
            "scopes": k.scopes.split(","),
            "created_at": k.created_at,
            "expires_at": k.expires_at,
        }
        for k in keys
    ]


async def revoke_api_key(db: AsyncSession, key_id: int, user_id: int) -> bool:
    """Revoke an API key."""
    stmt = select(ApiKey).where(
        ApiKey.id == key_id,
        ApiKey.user_id == user_id,
    )
    result = await db.execute(stmt)
    db_key = result.scalar_one_or_none()

    if not db_key:
        return False

    db_key.is_active = 0
    await db.commit()
    return True
