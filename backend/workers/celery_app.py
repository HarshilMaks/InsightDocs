"""Celery configuration and tasks."""
import ssl
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from celery import Celery
from backend.config import settings
from backend.core.logging import configure_logging

# Structured logging for worker processes
configure_logging()


def _fix_rediss_url(url: str) -> str:
    """Append ?ssl_cert_reqs=CERT_NONE to a rediss:// URL if not already present.

    Celery's Redis backend URL parser requires this query param explicitly,
    even when redis_backend_use_ssl is set in the config.
    """
    if not url.startswith("rediss://"):
        return url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "ssl_cert_reqs" not in qs:
        sep = "&" if parsed.query else ""
        new_query = parsed.query + sep + "ssl_cert_reqs=CERT_NONE"
        parsed = parsed._replace(query=new_query)
    return urlunparse(parsed)


# Fix URLs before Celery sees them
_broker_url = _fix_rediss_url(settings.celery_broker_url)
_backend_url = _fix_rediss_url(settings.celery_result_backend)

# Initialize Celery app
celery_app = Celery(
    "insightdocs",
    broker=_broker_url,
    backend=_backend_url,
)

# SSL config required for rediss:// (TLS) connections like Upstash
_redis_ssl_options = {}
if _broker_url.startswith("rediss://"):
    _redis_ssl_options = {"ssl_cert_reqs": ssl.CERT_NONE}

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    # GitHub-hosted workers are intentionally short-lived. A job is only
    # acknowledged after it succeeds so an interrupted worker can retry it.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    broker_use_ssl=_redis_ssl_options if _redis_ssl_options else None,
    redis_backend_use_ssl=_redis_ssl_options if _redis_ssl_options else None,
    beat_schedule={
        'cleanup-old-tasks-daily': {
            'task': 'insightdocs.cleanup_old_tasks',
            'schedule': 86400.0,  # Run once per day (24h in seconds)
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['backend.workers'])
