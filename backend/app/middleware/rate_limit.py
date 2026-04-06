import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def _create_limiter() -> Limiter:
    """
    Create a rate limiter, falling back to in-memory storage if Redis is unavailable.
    In-memory is fine for single-instance dev; use Redis for multi-instance production.
    """
    try:
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=settings.REDIS_URL,
            default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
        )
        logger.info("Rate limiter using Redis backend: %s", settings.REDIS_URL)
        return limiter
    except Exception as e:
        logger.warning(
            "Redis unavailable for rate limiting (%s). Falling back to in-memory storage.", e
        )
        return Limiter(
            key_func=get_remote_address,
            storage_uri="memory://",
            default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
        )

limiter = _create_limiter()


def get_limiter() -> Limiter:
    return limiter
