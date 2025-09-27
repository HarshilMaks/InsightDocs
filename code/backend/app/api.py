"""
API Router
Core endpoints for document ingestion, retrieval, and health checks.
"""

import uuid
import time
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Request, BackgroundTasks
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
from services.milvus import milvus_client
from services.rag import rag_service
from services.files import file_service

router = APIRouter()
settings = get_settings()


# RAG Query Endpoint
@router.post("/query", response_model=QueryResponse, summary="Query documents")
async def query_documents(
    query: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Process user query with Milvus + Gemini"""
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
    """Upload a file, process embeddings, and save metadata"""
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
    """Return all documents from metadata DB"""
    try:
        docs = await file_service.list_documents(skip, limit, db)
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


# Health Check
@router.get("/health", response_model=HealthCheckResponse, summary="Health check")
async def health_check() -> HealthCheckResponse:
    """Check DB + Milvus + S3 connectivity"""
    try:
        # DB health
        db_ok = True  # TODO: real check
        # Milvus health
        milvus_ok = milvus_client.ping()
        # TODO: add S3 check

        overall = "healthy" if (db_ok and milvus_ok) else "unhealthy"
        return HealthCheckResponse(
            status=overall,
            service="InsightOps API",
            timestamp=time.time(),
            version=settings.app.version,
            dependencies={
                "database": "healthy" if db_ok else "unhealthy",
                "milvus": "healthy" if milvus_ok else "unhealthy",
                "s3": "healthy"  # placeholder
            }
        )
    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            service="InsightOps API",
            timestamp=time.time(),
            version=settings.app.version,
            dependencies={"error": str(e)}
        )