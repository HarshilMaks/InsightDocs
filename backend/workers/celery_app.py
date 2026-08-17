"""Celery configuration and tasks."""
import ssl
from celery import Celery
from backend.config import settings
from backend.core.logging import configure_logging

# Structured logging for worker processes
configure_logging()

# Initialize Celery app
celery_app = Celery(
    "insightdocs",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# SSL config required for rediss:// (TLS) connections like Upstash
_redis_ssl_options = {}
if settings.celery_broker_url.startswith("rediss://"):
    _redis_ssl_options = {"ssl_cert_reqs": ssl.CERT_NONE}

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
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
