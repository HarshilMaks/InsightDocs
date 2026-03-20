from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.security import decode_token
from backend.config import settings


def _rate_limit_key(request: Request) -> str:
    """Rate-limit by authenticated user when possible, else by client IP."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        token_data = decode_token(token)
        if token_data and token_data.user_id:
            return f"user:{token_data.user_id}"

    return f"ip:{get_remote_address(request)}"


# Initialize limiter with Redis if available, or memory fallback.
limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=settings.redis_url,
    default_limits=["200 per day", "50 per hour"]
)
