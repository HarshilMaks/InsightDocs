"""
API Router
Core endpoints for document ingestion, retrieval, and health checks.
"""

import uuid
from datetime import datetime
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import get_settings
from models.schemas import (
    QueryRequest,
    QueryResponse,
    DocumentUploadResponse,
    DocumentListResponse,
    HealthCheckResponse,
)
from services.rag_service import RAGService
from services.file_service import FileService

router = APIRouter()
settings = get_settings()

# Service singletons/instances
rag_service = RAGService()
file_service = FileService()


# RAG Query Endpoint
@router.post("/query", response_model=QueryResponse, summary="Query documents")
async def query_documents(
    query: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Process user query with RAG pipeline (Milvus + LLM)."""
    try:
        response = await rag_service.query_documents(query, db)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Document Upload Endpoint
@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    summary="Upload document"
)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload file, process embeddings, and save metadata."""
    try:
        document_id = str(uuid.uuid4())
        result = await file_service.upload_and_process(file, document_id, db, background_tasks)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# List Documents
@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List documents"
)
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """Return all documents from metadata DB."""
    try:
        docs = await file_service.list_documents(skip, limit, db)
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


# Health Check
@router.get("/health", response_model=HealthCheckResponse, summary="Health check")
async def health_check() -> HealthCheckResponse:
    """Check DB + Milvus + S3 connectivity."""
    try:
        # TODO: real checks here
        db_ok = True
        milvus_ok = await rag_service.check_milvus()
        s3_ok = True  # placeholder

        overall = "healthy" if (db_ok and milvus_ok and s3_ok) else "unhealthy"
        return HealthCheckResponse(
            status=overall,
            service="InsightOps API",
            timestamp=datetime.utcnow(),
            version=settings.app.version,
        )
    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            service="InsightOps API",
            timestamp=datetime.utcnow(),
            version=settings.app.version,
        )