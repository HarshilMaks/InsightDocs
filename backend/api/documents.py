"""API endpoints for document management."""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
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
from backend.core.security import get_current_user
from backend.workers.tasks import process_document_task, generate_podcast_task
from backend.utils.document_processor import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE
from backend.utils.llm_client import LLMClient

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
async def upload_document(
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
            args=[document.id, temp_path, file.filename]
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
async def list_documents(
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
async def get_document(
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
async def delete_document(
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


@router.post("/{document_id}/summarize")
async def summarize_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an LLM summary of a processed document (user must own it)."""
    text = _get_document_text(document_id, db, current_user)
    llm = LLMClient()
    summary = await llm.summarize(text)
    return {"document_id": document_id, "summary": summary}


@router.post("/{document_id}/quiz")
async def generate_quiz(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate quiz questions from a processed document (user must own it)."""
    text = _get_document_text(document_id, db, current_user)
    llm = LLMClient()
    quiz = await llm.generate_quiz(text)
    return {"document_id": document_id, "quiz": quiz}


@router.post("/{document_id}/mindmap")
async def generate_mindmap(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a mind map (concepts + relationships) from a processed document (user must own it)."""
    text = _get_document_text(document_id, db, current_user)
    llm = LLMClient()
    mindmap = await llm.generate_mindmap(text)
    return {"document_id": document_id, "mindmap": mindmap}


@router.post("/{document_id}/generate-podcast")
async def generate_podcast(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger async podcast generation for a document (user must own it)."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document processing not complete")

    task = generate_podcast_task.apply_async(args=[document_id])

    # Create Task record
    task_record = Task(
        id=task.id,
        task_type="podcast_generation",
        status=TaskStatus.PENDING,
        progress=0.0,
        user_id=current_user.id,
        document_id=document_id,
    )
    db.add(task_record)
    db.commit()

    return {
        "success": True,
        "task_id": task.id,
        "message": "Podcast generation started"
    }


@router.get("/{document_id}/podcast")
async def get_podcast(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get podcast audio for a document (user must own it)."""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not doc or not doc.has_podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    from backend.storage.file_storage import FileStorage
    storage = FileStorage()
    url = storage.get_file_url(doc.podcast_s3_key)
    return {"url": url, "duration": doc.podcast_duration}
