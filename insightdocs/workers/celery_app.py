"""Celery configuration and tasks."""
from celery import Celery
from insightdocs.config import settings

# Initialize Celery app
celery_app = Celery(
    "insightdocs",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

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
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['insightdocs.workers'])
