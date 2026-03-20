"""Celery tasks for async processing."""
import asyncio
from typing import Dict, Any, Optional
import logging
from backend.workers.celery_app import celery_app
from backend.agents import OrchestratorAgent, AnalysisAgent
from backend.models import get_db, Task, Document, TaskStatus
from backend.models.schemas import User
from backend.core.security import decrypt_api_key
from sqlalchemy.orm import Session
import os

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _create_db_session() -> tuple[Session, Any]:
    """Create an owned DB session for worker tasks."""
    db_gen = get_db()
    db = next(db_gen)
    return db, db_gen


def _close_db_session(db_gen: Any) -> None:
    """Close an owned DB session generator created by _create_db_session."""
    try:
        db_gen.close()
    except Exception as e:
        logger.warning(f"Failed to close DB generator: {e}")


def _update_task(db: Session, task_id: str, **kwargs):
    """Update a task record."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        for k, v in kwargs.items():
            setattr(task, k, v)
        db.commit()


def _update_document(db: Session, doc_id: str, user_id: Optional[str] = None, **kwargs):
    """Update a document record."""
    query = db.query(Document).filter(Document.id == doc_id)
    if user_id:
        query = query.filter(Document.user_id == user_id)
    doc = query.first()
    if doc:
        for k, v in kwargs.items():
            setattr(doc, k, v)
        db.commit()


def _get_owned_document(db: Session, doc_id: str, user_id: Optional[str]) -> Optional[Document]:
    """Fetch a document scoped to the given owner."""
    if not user_id:
        return None
    return db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user_id,
    ).first()


def _get_user_api_key(db: Session, user_id: Optional[str]) -> Optional[str]:
    """Helper to retrieve decrypted API key for a user if BYOK is enabled."""
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.byok_enabled and user.gemini_api_key_encrypted:
        try:
            return decrypt_api_key(user.gemini_api_key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt API key for user {user_id}: {e}")
            return None
    return None


@celery_app.task(bind=True, name="insightdocs.process_document")
def process_document_task(self, document_id: str, file_path: str, filename: str, user_id: str = None):
    """Async task to process a document through the agent pipeline."""
    logger.info(f"Processing document {document_id}: {filename} (User: {user_id})")

    db, db_gen = _create_db_session()
    if not user_id:
        error_msg = "user_id is required for process_document_task"
        logger.error(error_msg)
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=error_msg)
        return {"success": False, "error": error_msg}

    if not _get_owned_document(db, document_id, user_id):
        error_msg = f"Document {document_id} not found for user {user_id}"
        logger.error(error_msg)
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=error_msg)
        return {"success": False, "error": error_msg}

    api_key = _get_user_api_key(db, user_id)
    
    try:
        _update_task(db, self.request.id, status=TaskStatus.PROCESSING, progress=10.0)
        _update_document(db, document_id, user_id=user_id, status=TaskStatus.PROCESSING)

        orchestrator = OrchestratorAgent(api_key=api_key)
        
        # Ensure file path is absolute
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        result = _run_async(orchestrator.process({
            "workflow_type": "ingest_and_analyze",
            "file_path": file_path,
            "filename": filename,
            "task_id": self.request.id,
            "document_id": document_id,
            "user_id": user_id,  # NEW: Pass user_id for tenant isolation
        }))

        if result.get("success"):
            _update_task(db, self.request.id,
                         status=TaskStatus.COMPLETED, result=result, progress=100.0)
            _update_document(db, document_id, user_id=user_id, status=TaskStatus.COMPLETED)
        else:
            error_msg = result.get("error", "Unknown processing error")
            _update_task(db, self.request.id,
                         status=TaskStatus.FAILED, error=error_msg)
            _update_document(db, document_id,
                             user_id=user_id,
                             status=TaskStatus.FAILED,
                             error_message=error_msg)

        logger.info(f"Completed processing document {document_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=str(e))
        _update_document(db, document_id, user_id=user_id, status=TaskStatus.FAILED, error_message=str(e))
        # Don't re-raise if we want to avoid Celery retries for fatal errors
        return {"success": False, "error": str(e)}
    finally:
        _close_db_session(db_gen)


@celery_app.task(bind=True, name="insightdocs.generate_embeddings")
def generate_embeddings_task(self, document_id: str, chunks: list, user_id: str = None):
    """Async task to generate embeddings for document chunks."""
    logger.info(f"Generating embeddings for document {document_id}")

    db, db_gen = _create_db_session()
    if not user_id:
        error_msg = "user_id is required for generate_embeddings_task"
        logger.error(error_msg)
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=error_msg)
        return {"success": False, "error": error_msg}

    if not _get_owned_document(db, document_id, user_id):
        error_msg = f"Document {document_id} not found for user {user_id}"
        logger.error(error_msg)
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=error_msg)
        return {"success": False, "error": error_msg}

    api_key = _get_user_api_key(db, user_id)

    try:
        _update_task(db, self.request.id, status=TaskStatus.PROCESSING)

        analysis_agent = AnalysisAgent(api_key=api_key)
        result = _run_async(analysis_agent.process({
            "task_type": "embed",
            "chunks": chunks,
            "metadata": {
                "document_id": document_id,
                "user_id": user_id,
            }
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
        return {"success": False, "error": str(e)}
    finally:
        _close_db_session(db_gen)


@celery_app.task(bind=True, name="insightdocs.generate_podcast")
def generate_podcast_task(self, document_id: str, user_id: str = None):
    """Async task to generate a podcast audio for a document."""
    logger.info(f"Generating podcast for document {document_id}")

    db, db_gen = _create_db_session()
    if not user_id:
        error_msg = "user_id is required for generate_podcast_task"
        logger.error(error_msg)
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=error_msg)
        return {"success": False, "error": error_msg}

    api_key = _get_user_api_key(db, user_id)

    try:
        _update_task(db, self.request.id, status=TaskStatus.PROCESSING)

        # 1. Get document content
        from backend.models import DocumentChunk
        doc = _get_owned_document(db, document_id, user_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found for user {user_id}")

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        if not chunks:
            raise ValueError("No content found for this document")

        text = "\n\n".join(c.content for c in chunks)
        # 2. Generate podcast script via LLM
        from backend.utils.llm_client import LLMClient
        llm = LLMClient(api_key=api_key)
        
        # Check if LLMClient supports async generation method directly, if not wrap it
        # Assuming generate_podcast_script is async
        script = _run_async(llm.generate_podcast_script(text, doc.filename))

        # 3. Generate audio using PodcastGenerator
        from backend.utils.podcast_generator import PodcastGenerator
        import tempfile
        from backend.storage.file_storage import FileStorage

        storage = FileStorage()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        # This part might be CPU intensive/blocking, could run in executor if needed
        audio_bytes, duration = PodcastGenerator.generate_podcast_from_text(
            script, output_path=tmp_path
        )

        s3_key = None
        if audio_bytes and os.path.exists(tmp_path):
            # 4. Store audio in S3
            podcast_filename = f"podcast_{document_id}.mp3"
            
            # FileStorage methods are async
            s3_key = _run_async(storage.store_file(tmp_path, podcast_filename))

            # 5. Update Document record
            doc.has_podcast = True
            doc.podcast_s3_key = s3_key
            doc.podcast_duration = duration
            db.commit()

            _update_task(db, self.request.id,
                         status=TaskStatus.COMPLETED,
                         result={"s3_key": s3_key, "duration": duration},
                         progress=100.0)
            logger.info(f"Podcast generated for document {document_id}: {s3_key}")
            return {"success": True, "s3_key": s3_key, "duration": duration}
        else:
            _update_task(db, self.request.id,
                         status=TaskStatus.FAILED,
                         error="Audio generation failed or produced no output")
            return {"success": False, "error": "Audio generation failed or produced no output"}

    except Exception as e:
        logger.error(f"Error generating podcast: {e}", exc_info=True)
        _update_task(db, self.request.id, status=TaskStatus.FAILED, error=str(e))
        return {"success": False, "error": str(e)}
    finally:
        try:
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up temporary podcast file: {cleanup_error}")
        _close_db_session(db_gen)


@celery_app.task(name="insightdocs.cleanup_old_tasks")
def cleanup_old_tasks():
    """Periodic task to clean up old completed tasks."""
    logger.info("Running cleanup of old tasks")
    db_gen = None
    try:
        from datetime import datetime, timedelta
        db, db_gen = _create_db_session()
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
        return {"error": str(e)}
    finally:
        if db_gen is not None:
            _close_db_session(db_gen)
