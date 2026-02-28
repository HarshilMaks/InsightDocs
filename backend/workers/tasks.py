"""Celery tasks for async processing."""
import asyncio
from typing import Dict, Any
import logging
from backend.workers.celery_app import celery_app
from backend.agents import OrchestratorAgent
from backend.models import get_db, Task, Document, TaskStatus
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous Celery task."""
    return asyncio.run(coro)


def _update_task(db: Session, task_id: str, **kwargs):
    """Update a task record."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        for k, v in kwargs.items():
            setattr(task, k, v)
        db.commit()


def _update_document(db: Session, doc_id: str, **kwargs):
    """Update a document record."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        for k, v in kwargs.items():
            setattr(doc, k, v)
        db.commit()


@celery_app.task(bind=True, name="insightdocs.process_document")
def process_document_task(self, document_id: str, file_path: str, filename: str):
    """Async task to process a document through the agent pipeline."""
    logger.info(f"Processing document {document_id}: {filename}")

    db = next(get_db())
    try:
        _update_task(db, self.request.id, status=TaskStatus.PROCESSING)
        _update_document(db, document_id, status=TaskStatus.PROCESSING)

        orchestrator = OrchestratorAgent()
        result = _run_async(orchestrator.process({
            "workflow_type": "ingest_and_analyze",
            "file_path": file_path,
            "filename": filename,
            "task_id": self.request.id,
            "document_id": document_id,
        }))

        if result.get("success"):
            _update_task(db, self.request.id,
                         status=TaskStatus.COMPLETED, result=result, progress=100.0)
            _update_document(db, document_id, status=TaskStatus.COMPLETED)
        else:
            _update_task(db, self.request.id,
                         status=TaskStatus.FAILED, error=result.get("error", "Unknown error"))
            _update_document(db, document_id,
                             status=TaskStatus.FAILED, error_message=result.get("error"))

        logger.info(f"Completed processing document {document_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=str(e))
        _update_document(db, document_id, status=TaskStatus.FAILED, error_message=str(e))
        raise


@celery_app.task(bind=True, name="insightdocs.generate_embeddings")
def generate_embeddings_task(self, document_id: str, chunks: list):
    """Async task to generate embeddings for document chunks."""
    logger.info(f"Generating embeddings for document {document_id}")

    db = next(get_db())
    try:
        _update_task(db, self.request.id, status=TaskStatus.PROCESSING)

        from backend.agents import AnalysisAgent
        analysis_agent = AnalysisAgent()
        result = _run_async(analysis_agent.process({
            "task_type": "embed",
            "chunks": chunks,
            "metadata": {"document_id": document_id}
        }))

        if result.get("success"):
            _update_task(db, self.request.id,
                         status=TaskStatus.COMPLETED, result=result, progress=100.0)
        else:
            _update_task(db, self.request.id,
                         status=TaskStatus.FAILED, error=result.get("error", "Unknown error"))

        logger.info(f"Completed embedding generation for document {document_id}")
        return result

    except Exception as e:
        logger.error(f"Error generating embeddings for document {document_id}: {e}")
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=str(e))
        raise


@celery_app.task(name="insightdocs.cleanup_old_tasks")
def cleanup_old_tasks():
    """Periodic task to clean up old completed tasks."""
    logger.info("Running cleanup of old tasks")
    try:
        from datetime import datetime, timedelta
        db = next(get_db())
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        old_tasks = db.query(Task).filter(
            Task.created_at < cutoff_date,
            Task.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED])
        ).all()
        count = len(old_tasks)
        for task in old_tasks:
            db.delete(task)
        db.commit()
        logger.info(f"Cleaned up {count} old tasks")
        return {"cleaned": count}
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}")
        raise
