"""
Pydantic schemas for API requests and responses
(Merged from InsightDocs and Insight projects)
"""

from pydantic import BaseModel, Field, EmailStr, constr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# --- Base Schema ---

class BaseSchema(BaseModel):
    """Base schema with shared config"""
    class Config:
        from_attributes = True
        use_enum_values = True
        validate_assignment = True

# --- Enums (from Insight) ---

class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"

class QueryType(str, Enum):
    GENERAL = "general"
    SUMMARY = "summary"
    FACTUAL = "factual"

# --- User & Auth Schemas (from Insight) ---

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

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str

class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
class TokenData(BaseSchema):
    user_id: Optional[str] = None

class LoginResponse(BaseSchema):
    token: Token
    user: UserResponse

# --- Document Schemas (Merged) ---

class DocumentResponse(BaseSchema):
    """Response model for a single document."""
    id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    s3_bucket: str
    s3_key: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DocumentUploadResponse(BaseSchema):
    """Response for a successful document upload."""
    success: bool
    message: str
    document: DocumentResponse
    task_id: str

class DocumentListResponse(BaseSchema):
    """Paginated list of documents."""
    documents: List[DocumentResponse]
    total: int

# --- Query Schemas (Merged) ---

class DocumentFilter(BaseSchema):
    document_ids: Optional[List[str]] = None
    file_types: Optional[List[FileType]] = None

class QueryRequest(BaseSchema):
    """Request model for RAG query."""
    query: str = Field(..., min_length=1, max_length=2000)
    query_type: QueryType = QueryType.GENERAL
    top_k: int = Field(5, ge=1, le=50)
    filters: Optional[DocumentFilter] = None

class SourceReference(BaseSchema):
    """Reference to a source document chunk."""
    document_id: str
    filename: str
    chunk_index: int
    content: str
    relevance_score: float
    milvus_id: Optional[str] = None

class QueryResponse(BaseSchema):
    """Response model for document queries."""
    success: bool
    query: str
    answer: str
    sources: List[SourceReference]
    metadata: Optional[Dict[str, Any]] = None

# --- Task Schemas (from InsightDocs, updated) ---

class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    status: str # Uses the string value of the TaskStatus enum
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    document_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# --- System Schemas ---

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    components: Dict[str, str]

class ErrorResponse(BaseModel):
    detail: str