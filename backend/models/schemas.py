"""
SQLAlchemy Database Models for InsightDocs
(Merged from InsightDocs and Insight projects)
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint, Column, String, Integer, Boolean, DateTime, Text,
    ForeignKey, Float, JSON, Index, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base  # Use the Base from your project's database.py

# --- Helper Functions ---

def _generate_uuid():
    """Generate string UUIDs for primary keys"""
    return str(uuid.uuid4())

def utc_now():
    """UTC timestamp generator"""
    return datetime.now(timezone.utc)

# --- Mixin ---

class TimestampMixin:
    """Adds created_at and updated_at timestamp columns to a model."""
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

# --- TaskStatus Enum ---

class TaskStatus(str, PyEnum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# --- Main Models ---

class User(Base, TimestampMixin):
    """
    System user
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(20), default="member", nullable=False)  # "admin" or "member"

    # BYOK Fields
    gemini_api_key_encrypted = Column(String(500), nullable=True)
    byok_enabled = Column(Boolean, default=False)

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}', role='{self.role}')>"


class Document(Base, TimestampMixin):
    """
    Metadata for uploaded documents
    """
    __tablename__ = "documents"

    # Core fields
    id = Column(String, primary_key=True, default=_generate_uuid)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # S3 Storage fields (from Insight)
    s3_bucket = Column(String(100), nullable=False)
    s3_key = Column(String(500), nullable=False)

    # Status fields (from InsightDocs)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True) # Renamed from metadata
    
    # OCR Fields
    is_scanned = Column(Boolean, default=False)
    ocr_confidence = Column(Float, nullable=True)
    
    # Relationships
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="documents")
    
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="document")

    __table_args__ = (
        Index("ix_documents_user_status", "user_id", "status"),
    )

    def __repr__(self):
        return f"<Document(id='{self.id}', filename='{self.filename}', status='{self.status}')>"


class DocumentChunk(Base, TimestampMixin):
    """
    Document chunks mapped to embeddings (Merged Model)
    """
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=_generate_uuid)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # Embedding info
    embedding_model = Column(String(100), nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    milvus_id = Column(String(100), nullable=True) # Renamed from embedding_id
    
    # Spatial positioning (bounding boxes for precise citations)
    page_number = Column(Integer, nullable=True)
    bbox_x1 = Column(Float, nullable=True)  # Left coordinate
    bbox_y1 = Column(Float, nullable=True)  # Top coordinate
    bbox_x2 = Column(Float, nullable=True)  # Right coordinate
    bbox_y2 = Column(Float, nullable=True)  # Bottom coordinate

    # Structural metadata (section-aware, table-atomic chunking)
    section_title = Column(String(500), nullable=True)
    chunk_type = Column(String(20), nullable=True)  # "text" | "table" | None (legacy chunks)
    parent_chunk_id = Column(
        String, ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    document = relationship("Document", back_populates="chunks")
    parent_chunk = relationship("DocumentChunk", remote_side=[id])

    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index"),
        Index("ix_chunks_doc_milvus", "document_id", "milvus_id"),
        Index("ix_chunks_parent", "parent_chunk_id"),
    )

    def __repr__(self):
        return f"<DocumentChunk(id='{self.id}', doc_id='{self.document_id}', idx={self.chunk_index})>"


class Task(Base, TimestampMixin):
    """
    Task tracking model for Celery (from InsightDocs, with User link added)
    """
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=_generate_uuid)
    task_type = Column(String(50), nullable=False)
    
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    progress = Column(Float, default=0.0)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Relationships
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", back_populates="tasks")
    
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    document = relationship("Document", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id='{self.id}', type='{self.task_type}', status='{self.status}')>"


class Query(Base, TimestampMixin):
    """
    Query history model (Merged Model)
    """
    __tablename__ = "queries"
    
    id = Column(String, primary_key=True, default=_generate_uuid)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True) # Renamed from response
    conversation_id = Column(String(100), nullable=True)
    turn_index = Column(Integer, nullable=True)
    
    # Detailed logging (from Insight)
    response_time = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    tokens_used = Column(Integer, default=0, nullable=True)
    model_name = Column(String(100), nullable=True)
    
    # Context (from Insight, renamed from context_documents)
    sources = Column(JSON, nullable=True)

    # Relationships
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", back_populates="queries")
    evidence_gate_runs = relationship(
        "EvidenceGateRun", back_populates="query", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_queries_user_created", "user_id", "created_at"),
        Index("ix_queries_user_conversation_turn", "user_id", "conversation_id", "turn_index"),
    )

    def __repr__(self):
        return f"<Query(id='{self.id}', user_id='{self.user_id}')>"


class EvidenceGateRun(Base, TimestampMixin):
    """Immutable, query-bound audit result for one versioned evidence policy run."""
    __tablename__ = "evidence_gate_runs"

    id = Column(String, primary_key=True, default=_generate_uuid)
    query_id = Column(String, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    # Denormalized tenant metadata aids auditing/indexing; authorization must still
    # join through Query ownership so this field is never an authorization shortcut.
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    attempt = Column(Integer, nullable=False, default=1)
    policy_version = Column(String(64), nullable=False)
    mode = Column(String(16), nullable=False, default="shadow")
    status = Column(String(16), nullable=False)
    action = Column(String(16), nullable=True)
    candidate_answer_sha256 = Column(String(64), nullable=False)
    delivered_answer_sha256 = Column(String(64), nullable=False)
    source_snapshot_sha256 = Column(String(64), nullable=False)
    verifier_model = Column(String(100), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    claim_count = Column(Integer, nullable=False, default=0)
    supported_count = Column(Integer, nullable=False, default=0)
    unsupported_count = Column(Integer, nullable=False, default=0)
    unverified_count = Column(Integer, nullable=False, default=0)
    error_code = Column(String(64), nullable=True)
    error_detail = Column(Text, nullable=True)

    query = relationship("Query", back_populates="evidence_gate_runs")
    claims = relationship(
        "EvidenceGateClaim", back_populates="gate_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "query_id", "policy_version", "attempt",
            name="uq_evidence_gate_runs_query_policy_attempt",
        ),
        CheckConstraint(
            "mode IN ('shadow', 'annotate', 'enforce')",
            name="ck_evidence_gate_runs_mode",
        ),
        CheckConstraint(
            "status IN ('passed', 'failed', 'degraded', 'abstained')",
            name="ck_evidence_gate_runs_status",
        ),
        CheckConstraint(
            "action IS NULL OR action IN ('allow', 'annotate', 'abstain')",
            name="ck_evidence_gate_runs_action",
        ),
        Index("ix_evidence_gate_runs_user_created", "user_id", "created_at"),
        Index("ix_evidence_gate_runs_query_created", "query_id", "created_at"),
    )

    def __repr__(self):
        return (
            f"<EvidenceGateRun(id='{self.id}', query_id='{self.query_id}', "
            f"status='{self.status}')>"
        )


class EvidenceGateClaim(Base, TimestampMixin):
    """A claim-level assessment that references an immutable query source snapshot."""
    __tablename__ = "evidence_gate_claims"

    id = Column(String, primary_key=True, default=_generate_uuid)
    gate_run_id = Column(
        String, ForeignKey("evidence_gate_runs.id", ondelete="CASCADE"), nullable=False
    )
    ordinal = Column(Integer, nullable=False)
    claim_text = Column(Text, nullable=False)
    claim_sha256 = Column(String(64), nullable=False)
    verdict = Column(String(16), nullable=False)
    reason = Column(Text, nullable=True)
    supporting_source_numbers = Column(JSON, nullable=False, default=list)

    gate_run = relationship("EvidenceGateRun", back_populates="claims")

    __table_args__ = (
        UniqueConstraint("gate_run_id", "ordinal", name="uq_evidence_gate_claims_run_ordinal"),
        CheckConstraint(
            "verdict IN ('supported', 'unsupported', 'unverified')",
            name="ck_evidence_gate_claims_verdict",
        ),
        Index("ix_evidence_gate_claims_run_verdict", "gate_run_id", "verdict"),
    )

    def __repr__(self):
        return (
            f"<EvidenceGateClaim(id='{self.id}', gate_run_id='{self.gate_run_id}', "
            f"ordinal={self.ordinal})>"
        )
