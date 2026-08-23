"""
Pydantic schemas for API requests and responses.
(Merged from InsightOps and Insight projects)
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Literal
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
        protected_namespaces = ()

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
    role: str = "member"

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
# Evidence Workspace schemas
# ---------------------------------------------------------

class EvidenceWorkspaceCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    document_ids: List[str] = Field(default_factory=list, max_length=100)


class EvidenceWorkspaceUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)


class EvidenceWorkspaceListItem(BaseSchema):
    id: str
    name: str
    description: Optional[str] = None
    document_count: int
    created_at: datetime
    updated_at: datetime


class EvidenceWorkspaceResponse(EvidenceWorkspaceListItem):
    documents: List[DocumentResponse] = Field(default_factory=list)


class EvidenceWorkspaceListResponse(BaseSchema):
    workspaces: List[EvidenceWorkspaceListItem]
    total: int


# ---------------------------------------------------------
# Query Schemas (Updated)
# ---------------------------------------------------------
# ---------------------------------------------------------

class BoundingBox(BaseSchema):
    """Spatial coordinates for text positioning"""
    x1: float = Field(..., description="Left coordinate")
    y1: float = Field(..., description="Top coordinate")
    x2: float = Field(..., description="Right coordinate")
    y2: float = Field(..., description="Bottom coordinate")
    page_number: Optional[int] = Field(None, description="Page number (1-indexed)")

class SourceReference(BaseSchema):
    source_number: int
    document_id: str
    document_name: str
    chunk_id: str
    chunk_index: int
    page_number: Optional[int] = None
    bbox: Optional[BoundingBox] = Field(None, description="Legacy bounding box for precise citation")
    bboxes: List[BoundingBox] = Field(default_factory=list, description="Exact separated text regions for this citation")
    section_title: Optional[str] = Field(None, description="Section heading this chunk belongs to")
    chunk_type: str = Field("text", description="Type of chunk: 'text' or 'table'")
    content_preview: str
    similarity_score: float
    citation_label: str

class ClaimVerification(BaseSchema):
    """Verification result for a single claim (sentence) in the generated answer."""
    claim: str = Field(..., description="The claim/sentence being verified")
    status: str = Field(
        ...,
        description='One of "supported", "unsupported", or "unverified" '
                     '("unverified" means the verification check itself could not run)',
    )
    supporting_sources: List[int] = Field(
        default_factory=list,
        description="source_number values (from QueryResponse.sources) that support this claim, if any",
    )
    reason: Optional[str] = Field(None, description="Short explanation, mainly populated for unsupported claims")

class QueryRequest(BaseSchema):
    query: str = Field(..., description="Query text")
    top_k: Optional[int] = Field(5, description="Number of results to retrieve")
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation thread ID for follow-up questions",
    )
    document_id: Optional[str] = Field(
        None,
        description="Restrict retrieval to a single document (e.g. the document workspace view). "
                     "If omitted, retrieval searches across all of the user's documents.",
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Restrict retrieval to the explicitly selected documents in an owner-scoped Evidence Workspace. "
                    "Mutually exclusive with document_id.",
    )

class EvidenceGateSummary(BaseSchema):
    """Compact optional metadata for a server-created shadow audit run."""

    id: str
    policy_version: str
    mode: str
    status: str
    action: Optional[str] = None
    claim_count: int
    supported_count: int
    unsupported_count: int
    unverified_count: int
    verified_at: datetime


class QueryResponse(BaseSchema):
    answer: str
    sources: List[SourceReference]
    query_id: str
    conversation_id: str
    turn_index: int
    query: str
    response_time: float
    confidence_score: Optional[float]
    tokens_used: Optional[int] = None
    claim_verifications: Optional[List[ClaimVerification]] = Field(
        None,
        description="Per-claim verification results, when verification ran successfully. "
                     "None if verification did not run (e.g. no context or a transient failure).",
    )
    evidence_gate: Optional[EvidenceGateSummary] = Field(
        None,
        description="Optional shadow-mode evidence audit metadata for this query.",
    )

class QueryHistoryItem(BaseSchema):
    id: str
    conversation_id: Optional[str] = None
    turn_index: Optional[int] = None
    document_id: Optional[str] = None
    workspace_id: Optional[str] = None
    query: str
    response: Optional[str] = None
    response_time: Optional[float] = None
    created_at: datetime

class QueryHistoryResponse(BaseSchema):
    queries: List[QueryHistoryItem]
    total: int

class ByokStatusResponse(BaseSchema):
    byok_enabled: bool
    has_api_key: bool
    user_id: str
    email: str
    status: str
    model_status: str
    message: str
    active_model: Optional[str] = None
    fallback_models: List[str] = Field(default_factory=list)
    available_models: List[str] = Field(default_factory=list)
    checked_at: Optional[datetime] = None

class ApiKeyResponse(BaseSchema):
    message: str
    byok_enabled: bool
    status: str
    model_status: str
    active_model: Optional[str] = None
    fallback_models: List[str] = Field(default_factory=list)
    available_models: List[str] = Field(default_factory=list)
    checked_at: Optional[datetime] = None

# ---------------------------------------------------------
# Task Schemas (Updated)
# ---------------------------------------------------------

class TaskStatusResponse(BaseSchema):
    task_id: str
    status: TaskStatus
    progress: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Task completion fraction. 0.0 = not started, 1.0 = complete.",
    )
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ---------------------------------------------------------
# System Schemas
# ---------------------------------------------------------

class HealthResponse(BaseSchema):
    status: str
    version: str
    components: Dict[str, str]


# ---------------------------------------------------------
# Evidence Gate reviewer schemas
# ---------------------------------------------------------

class EvidenceGateReviewQueueItem(BaseSchema):
    id: str
    query_id: str
    query_text: str
    status: str
    claim_count: int
    unsupported_count: int
    unverified_count: int
    review_status: str
    review_version: int
    created_at: datetime


class EvidenceGateReviewQueueResponse(BaseSchema):
    items: List[EvidenceGateReviewQueueItem]
    total: int


class EvidenceGateReviewSource(BaseSchema):
    """A source reconstructed only from the persisted query snapshot."""

    source_number: int
    document_id: str
    document_name: str
    chunk_id: str
    chunk_index: int
    page_number: Optional[int] = None
    bbox: Optional[BoundingBox] = None
    section_title: Optional[str] = None
    chunk_type: str = "text"
    content: str
    similarity_score: float
    citation_label: str


class EvidenceGateReviewClaim(BaseSchema):
    id: str
    ordinal: int
    claim_text: str
    verdict: str
    reason: Optional[str] = None
    supporting_source_numbers: List[int]
    sources: List[EvidenceGateReviewSource] = Field(default_factory=list)


class EvidenceGateReviewDecisionRequest(BaseSchema):
    decision: Literal["accepted", "rejected"]
    expected_version: int = Field(..., ge=0)
    note: Optional[str] = Field(None, max_length=2000)


class EvidenceGateReviewDecisionEvent(BaseSchema):
    id: str
    reviewer_id: Optional[str] = None
    decision: str
    note: Optional[str] = None
    expected_version: int
    result_version: int
    created_at: datetime


class EvidenceGateReviewDetail(BaseSchema):
    id: str
    query_id: str
    query_text: str
    response_text: Optional[str] = None
    policy_version: str
    mode: str
    status: str
    action: Optional[str] = None
    review_status: str
    review_version: int
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    claims: List[EvidenceGateReviewClaim]
    decision_history: List[EvidenceGateReviewDecisionEvent]
