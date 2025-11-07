"""Celery tasks for async processing."""
from typing import Dict, Any
import logging
from backend.workers.celery_app import celery_app
from backend.agents import OrchestratorAgent
from backend.models import get_db, Task, TaskStatus
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="insightdocs.process_document")
def process_document_task(self, document_id: int, file_path: str, filename: str):
    """Async task to process a document through the agent pipeline.
    
    Args:
        document_id: Database ID of the document
        file_path: Path to the document file
        filename: Original filename
    """
    logger.info(f"Processing document {document_id}: {filename}")
    
    try:
        # Update task status
        db = next(get_db())
        task = db.query(Task).filter(Task.id == self.request.id).first()
        if task:
            task.status = TaskStatus.PROCESSING
            db.commit()
        
        # Execute workflow through orchestrator
        orchestrator = OrchestratorAgent()
        result = orchestrator.process({
            "workflow_type": "ingest_and_analyze",
            "file_path": file_path,
            "filename": filename,
            "task_id": self.request.id,
            "document_id": document_id
        })
        
        # Update task with results
        if task:
            if result.get("success"):
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 100.0
            else:
                task.status = TaskStatus.FAILED
                task.error = result.get("error", "Unknown error")
            db.commit()
        
        logger.info(f"Completed processing document {document_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        
        # Update task with error
        db = next(get_db())
        task = db.query(Task).filter(Task.id == self.request.id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            db.commit()
        
        raise


@celery_app.task(bind=True, name="insightdocs.generate_embeddings")
def generate_embeddings_task(self, document_id: int, chunks: list):
    """Async task to generate embeddings for document chunks.
    
    Args:
        document_id: Database ID of the document
        chunks: List of text chunks
    """
    logger.info(f"Generating embeddings for document {document_id}")
    
    try:
        from backend.agents import AnalysisAgent
        
        # Update task status
        db = next(get_db())
        task = db.query(Task).filter(Task.id == self.request.id).first()
        if task:
            task.status = TaskStatus.PROCESSING
            db.commit()
        
        # Generate embeddings
        analysis_agent = AnalysisAgent()
        result = analysis_agent.process({
            "task_type": "embed",
            "chunks": chunks,
            "metadata": {"document_id": document_id}
        })
        
        # Update task with results
        if task:
            if result.get("success"):
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 100.0
            else:
                task.status = TaskStatus.FAILED
                task.error = result.get("error", "Unknown error")
            db.commit()
        
        logger.info(f"Completed embedding generation for document {document_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating embeddings for document {document_id}: {e}")
        
        # Update task with error
        db = next(get_db())
        task = db.query(Task).filter(Task.id == self.request.id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            db.commit()
        
        raise


@celery_app.task(name="insightdocs.cleanup_old_tasks")
def cleanup_old_tasks():
    """Periodic task to clean up old completed tasks."""
    logger.info("Running cleanup of old tasks")
    
    try:
        from datetime import datetime, timedelta
        db = next(get_db())
        
        # Delete tasks older than 30 days
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
