"""API endpoints for document management."""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import List
import logging
from pathlib import Path
from backend.api.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
)
from backend.models import get_db, Document, DocumentChunk, Task, TaskStatus
from backend.models.schemas import User
from backend.core.security import get_current_user, decrypt_api_key
from backend.utils.document_processor import MAX_FILE_SIZE, get_supported_extensions
from backend.utils.llm_client import GeminiAPIError, LLMClient
from backend.core.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


def _validate_upload(filename: str, content: bytes):
    """Validate file type and size."""
    ext = Path(filename).suffix.lower()
    supported = get_supported_extensions()
    if ext not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(supported))}"
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
        )


@router.post("/upload", response_model=DocumentUploadResponse)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document for processing (authenticated).

    The uploaded file is written directly to S3/MinIO before the Celery
    task is queued. Only the resulting object key is passed to the worker,
    so processing does not depend on a local temp file that a separate
    worker process or container cannot see.
    """
    try:
        content = await file.read()
        _validate_upload(file.filename, content)

        suffix = Path(file.filename).suffix

        try:
            from backend.storage.file_storage import FileStorage
            file_storage = FileStorage()
            s3_key = await file_storage.store_bytes(content, file.filename)
        except Exception as e:
            logger.error(f"Error uploading document to object storage: {e}")
            raise HTTPException(status_code=503, detail="Document storage is unavailable. Please try again.")

        document = Document(
            filename=file.filename,
            file_type=suffix,
            file_size=len(content),
            s3_bucket=file_storage.bucket_name,
            s3_key=s3_key,
            status=TaskStatus.PENDING,
            user_id=current_user.id  # Set to authenticated user
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        from backend.workers.tasks import process_document_task
        task = process_document_task.apply_async(
            args=[document.id, s3_key, file.filename, current_user.id]
        )

        # Create Task record so the worker can find and update it
        task_record = Task(
            id=task.id,
            task_type="document_processing",
            status=TaskStatus.PENDING,
            progress=0.0,
            user_id=current_user.id,  # Set to authenticated user
            document_id=document.id,
        )
        db.add(task_record)
        db.commit()

        logger.info(f"Uploaded document {document.id} to {s3_key}, task {task.id}")

        return DocumentUploadResponse(
            success=True,
            document_id=document.id,
            task_id=task.id,
            message="Document uploaded successfully. Processing started."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=DocumentListResponse)
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents for authenticated user."""
    try:
        # Filter by current user
        documents = db.query(Document).filter(
            Document.user_id == current_user.id
        ).offset(skip).limit(limit).all()
        total = db.query(Document).filter(
            Document.user_id == current_user.id
        ).count()
        return DocumentListResponse(documents=documents, total=total)
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
@limiter.limit("60/minute")
async def get_document(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document details (user must own it)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/file-url")
@limiter.limit("60/minute")
async def get_document_file_url(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return a short-lived, presigned URL for viewing the original document
    file (user must own it). The frontend document viewer uses this to
    render the source PDF for citation highlighting.

    A presigned URL is returned rather than proxying file bytes through
    this API: ownership is verified once per request here, the URL itself
    expires quickly (10 minutes), and the API process is not burdened with
    streaming potentially large files.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.s3_key or not document.s3_bucket:
        raise HTTPException(status_code=409, detail="Document file is not yet available.")

    try:
        from backend.storage.file_storage import FileStorage
        file_storage = FileStorage()
        url = file_storage.get_file_url(document.s3_key, expires_in=600)
    except Exception as e:
        logger.error(f"Error generating file URL for document {document_id}: {e}")
        raise HTTPException(status_code=503, detail="Unable to generate document file URL right now.")

    return {"document_id": document_id, "url": url, "expires_in": 600}


@router.delete("/{document_id}")
@limiter.limit("10/minute")
async def delete_document(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document (user must own it)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()
    return {"success": True, "message": "Document deleted successfully"}


# ------------------------------------------------------------------
# Feature endpoints: Summarize, Quiz, Mind Map
# ------------------------------------------------------------------

def _get_document_text(document_id: str, db: Session, current_user: User) -> str:
    """Fetch all chunk content for a document, joined as full text. User must own document."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Document not ready. Status: {doc.status.value}")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="No content found for this document.")
    return "\n\n".join(c.content for c in chunks)


def _get_user_llm_client(current_user: User) -> LLMClient:
    """Helper to initialize LLMClient with user's API key if present."""
    api_key = None
    if current_user.byok_enabled and current_user.gemini_api_key_encrypted:
        try:
            api_key = decrypt_api_key(current_user.gemini_api_key_encrypted)
        except Exception:
            logger.error(f"Failed to decrypt API key for user {current_user.id}")
            # Fallback to system key or fail gracefully depending on policy
            pass
    return LLMClient(api_key=api_key)

@router.post("/{document_id}/summarize")
@limiter.limit("10/minute")
async def summarize_document(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an LLM summary of a processed document (user must own it)."""
    try:
        text = _get_document_text(document_id, db, current_user)
        
        # Get decrypted API key if available
        api_key = None
        if current_user.byok_enabled and current_user.gemini_api_key_encrypted:
            try:
                api_key = decrypt_api_key(current_user.gemini_api_key_encrypted)
            except Exception:
                logger.error(f"Failed to decrypt API key for user {current_user.id}")
                pass

        llm = LLMClient(api_key=api_key)
        summary = await llm.summarize(text)

        return {"document_id": document_id, "summary": summary}
    except GeminiAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{document_id}/quiz")
@limiter.limit("10/minute")
async def generate_quiz(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate quiz questions from a processed document (user must own it)."""
    try:
        text = _get_document_text(document_id, db, current_user)
        llm = _get_user_llm_client(current_user)
        quiz = await llm.generate_quiz(text)
        return {"document_id": document_id, "quiz": quiz}
    except GeminiAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{document_id}/mindmap")
@limiter.limit("10/minute")
async def generate_mindmap(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a mind map (concepts + relationships) from a processed document (user must own it)."""
    try:
        text = _get_document_text(document_id, db, current_user)
        llm = _get_user_llm_client(current_user)
        mindmap = await llm.generate_mindmap(text)
        return {"document_id": document_id, "mindmap": mindmap}
    except GeminiAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
