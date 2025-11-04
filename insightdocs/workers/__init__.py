"""Workers package."""
from .celery_app import celery_app
from .tasks import process_document_task, generate_embeddings_task, cleanup_old_tasks

__all__ = [
    "celery_app",
    "process_document_task",
    "generate_embeddings_task",
    "cleanup_old_tasks",
]
