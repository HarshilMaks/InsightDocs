"""
Pydantic Schemas for API
Core data validation, serialization, and documentation models
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, constr, conint


# ---------------------------------------------------------
# Enums
# ---------------------------------------------------------

class DocumentStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"


class QueryType(str, Enum):
    GENERAL = "general"
    SUMMARY = "summary"
    FACTUAL = "factual"


# ---------------------------------------------------------
# Base Schema
# ---------------------------------------------------------

class BaseSchema(BaseModel):
    """Base schema with shared config"""
    class Config:
        from_attributes = True
        use_enum_values = True
        validate_assignment = True


# ---------------------------------------------------------
# User Schemas
# ---------------------------------------------------------

class UserBase(BaseSchema):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    password: constr(min_length=8, max_length=100)


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


# ---------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class LoginResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ---------------------------------------------------------
# Document Schemas
# ---------------------------------------------------------

class DocumentBase(BaseSchema):
    filename: str
    file_type: FileType
    file_size: int


class DocumentCreate(DocumentBase):
    user_id: str
    s3_key: str


class DocumentResponse(DocumentBase):
    id: str
    user_id: str
    status: DocumentStatus
    upload_date: datetime
    processed_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


# ---------------------------------------------------------
# Query Schemas
# ---------------------------------------------------------

class DocumentFilter(BaseSchema):
    document_ids: Optional[List[str]] = None
    file_types: Optional[List[FileType]] = None
    tags: Optional[List[str]] = None


class QueryRequest(BaseSchema):
    query: str = Field(..., min_length=1, max_length=2000)
    query_type: QueryType = QueryType.GENERAL
    max_results: int = Field(10, ge=1, le=50)
    min_similarity: float = Field(0.5, ge=0.0, le=1.0)
    include_citations: bool = True
    document_filters: Optional[DocumentFilter] = None


class SourceReference(BaseSchema):
    document_id: str
    document_name: str
    content_preview: str
    similarity_score: float


class QueryResponse(BaseSchema):
    answer: str
    sources: List[SourceReference]
    query: str
    response_time: float
    confidence_score: float


# ---------------------------------------------------------
# System Schemas
# ---------------------------------------------------------

class HealthCheckResponse(BaseSchema):
    status: str
    service: str
    timestamp: datetime
    version: str


class ErrorResponse(BaseSchema):
    error: str
    message: str
    request_id: Optional[str] = None


# ---------------------------------------------------------
# Export commonly used schemas
# ---------------------------------------------------------

__all__ = [
    "UserCreate", "UserResponse",
    "LoginRequest", "LoginResponse",
    "DocumentCreate", "DocumentResponse",
    "QueryRequest", "QueryResponse", "SourceReference",
    "HealthCheckResponse", "ErrorResponse",
    "DocumentStatus", "FileType", "QueryType"
]
