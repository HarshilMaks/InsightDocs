"""
Pydantic schemas for API requests and responses.
(Merged from InsightOps and Insight projects)
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# Import the Enum from your single source of truth: the database models
from backend.models.schemas import TaskStatus

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
# User & Auth Schemas (from Insight)
# ---------------------------------------------------------

class UserBase(BaseSchema):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    user_id: Optional[str] = None

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str

class LoginResponse(BaseSchema):
    token: Token
    user: UserResponse
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

# ---------------------------------------------------------
# Document Schemas (Updated)
# ---------------------------------------------------------

class DocumentResponse(BaseSchema):
    id: str
    user_id: str
    filename: str
    file_type: str
    file_size: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

class DocumentListResponse(BaseSchema):
    documents: List[DocumentResponse]
    total: int

class DocumentUploadResponse(BaseSchema):
    success: bool
    document_id: str
    task_id: str
    message: str

# ---------------------------------------------------------
# Query Schemas (Updated)
# ---------------------------------------------------------

class BoundingBox(BaseSchema):
    """Spatial coordinates for text positioning"""
    x1: float = Field(..., description="Left coordinate")
    y1: float = Field(..., description="Top coordinate")
    x2: float = Field(..., description="Right coordinate")
    y2: float = Field(..., description="Bottom coordinate")
    page_number: int = Field(..., description="Page number (1-indexed)")

class SourceReference(BaseSchema):
    document_id: str
    document_name: str
    content_preview: str
    similarity_score: float
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box for precise citation")

class QueryRequest(BaseSchema):
    query: str = Field(..., description="Query text")
    top_k: Optional[int] = Field(5, description="Number of results to retrieve")
    # You can add more filters here later, e.g.:
    # document_ids: Optional[List[str]] = None

class QueryResponse(BaseSchema):
    answer: str
    sources: List[SourceReference]
    query_id: str
    query: str
    response_time: float
    confidence_score: Optional[float]
    tokens_used: Optional[int] = None

# ---------------------------------------------------------
# Task Schemas (Updated)
# ---------------------------------------------------------

class TaskStatusResponse(BaseSchema):
    task_id: str
    status: TaskStatus
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ---------------------------------------------------------
# System Schemas
# ---------------------------------------------------------

class HealthResponse(BaseSchema):
    status: str
    version: str
    components: Dict[str, str]
