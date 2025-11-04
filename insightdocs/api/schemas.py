"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatusEnum(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadRequest(BaseModel):
    """Document upload request."""
    filename: str = Field(..., description="Name of the file")
    chunk_size: Optional[int] = Field(1000, description="Size of text chunks")


class DocumentUploadResponse(BaseModel):
    """Document upload response."""
    success: bool
    document_id: int
    task_id: str
    message: str


class QueryRequest(BaseModel):
    """Query request for RAG."""
    query: str = Field(..., description="Query text")
    top_k: Optional[int] = Field(5, description="Number of results to retrieve")


class QueryResponse(BaseModel):
    """Query response."""
    success: bool
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    status: TaskStatusEnum
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Document list response."""
    documents: List[Dict[str, Any]]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    components: Dict[str, str]
