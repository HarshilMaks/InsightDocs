"""API endpoints for document management."""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import List
import logging
from pathlib import Path
import tempfile
from backend.api.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
)
from backend.models import get_db, Document, DocumentChunk, Task, TaskStatus
from backend.models.schemas import User
from backend.core.security import get_current_user, decrypt_api_key
from backend.workers.tasks import process_document_task
from backend.utils.document_processor import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE
from backend.utils.llm_client import LLMClient
from backend.core.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


def _validate_upload(filename: str, content: bytes):
    """Validate file type and size."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
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
    """Upload a document for processing (authenticated)."""
    try:
        content = await file.read()
        _validate_upload(file.filename, content)

        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        document = Document(
            filename=file.filename,
            file_type=suffix,
            file_size=len(content),
            s3_bucket="temp",
            s3_key=temp_path,
            status=TaskStatus.PENDING,
            user_id=current_user.id  # Set to authenticated user
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        task = process_document_task.apply_async(
            args=[document.id, temp_path, file.filename, current_user.id]
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

        logger.info(f"Uploaded document {document.id}, task {task.id}")

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
    text = _get_document_text(document_id, db, current_user)
    llm = _get_user_llm_client(current_user)
    summary = await llm.summarize(text)
    return {"document_id": document_id, "summary": summary}


@router.post("/{document_id}/quiz")
@limiter.limit("10/minute")
async def generate_quiz(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate quiz questions from a processed document (user must own it)."""
    text = _get_document_text(document_id, db, current_user)
    llm = _get_user_llm_client(current_user)
    quiz = await llm.generate_quiz(text)
    return {"document_id": document_id, "quiz": quiz}


@router.post("/{document_id}/mindmap")
@limiter.limit("10/minute")
async def generate_mindmap(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a mind map (concepts + relationships) from a processed document (user must own it)."""
    text = _get_document_text(document_id, db, current_user)
    llm = _get_user_llm_client(current_user)
    mindmap = await llm.generate_mindmap(text)
    return {"document_id": document_id, "mindmap": mindmap}
