from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings

settings = get_settings()

# Initialize Rate Limiter using Redis as the backend for distributed scaling.
# If REDIS_URL is a dummy or not reachable, limits storage will fallback or error depending on config.
# For robust enterprise setups, we use RedisStorage by passing the URI.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)

def get_limiter() -> Limiter:
    return limiter
