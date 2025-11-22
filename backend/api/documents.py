"""API endpoints for document management."""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import logging
from pathlib import Path
import tempfile
from backend.api.schemas import (
    DocumentUploadResponse,
    DocumentListResponse
)
from backend.models import get_db, Document, TaskStatus
from backend.workers.tasks import process_document_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document for processing.
    
    Args:
        file: File to upload
        db: Database session
        
    Returns:
        Upload response with document ID and task ID
    """
    try:
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Create document record
        document = Document(
            filename=file.filename,
            file_type=suffix,
            file_size=len(content),
            s3_bucket="temp",  # Will be updated after S3 upload
            s3_key=temp_path,
            status=TaskStatus.PENDING,
            user_id="system"  # TODO: Replace with actual user_id from auth
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Start async processing task
        task = process_document_task.apply_async(
            args=[document.id, temp_path, file.filename]
        )
        
        logger.info(f"Uploaded document {document.id}, task {task.id}")
        
        return DocumentUploadResponse(
            success=True,
            document_id=document.id,
            task_id=task.id,
            message=f"Document uploaded successfully. Processing started."
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all documents.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of documents
    """
    try:
        documents = db.query(Document).offset(skip).limit(limit).all()
        total = db.query(Document).count()
        
        document_list = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status.value,
                "created_at": doc.created_at.isoformat(),
                "file_size": doc.file_size
            }
            for doc in documents
        ]
        
        return DocumentListResponse(
            documents=document_list,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get document details.
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        Document details
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "id": document.id,
            "filename": document.filename,
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "file_size": document.file_size,
            "file_type": document.file_type,
            "metadata": document.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document.
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        Deletion confirmation
    """
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        db.delete(document)
        db.commit()
        
        return {"success": True, "message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
