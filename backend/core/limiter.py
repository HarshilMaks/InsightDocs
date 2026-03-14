from slowapi import Limiter
from slowapi.util import get_remote_address
from backend.config import settings

# Initialize limiter with Redis if available, or memory fallback
# Using redis_url from settings
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=["200 per day", "50 per hour"]
)
