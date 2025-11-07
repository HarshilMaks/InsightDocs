"""
SQLAlchemy Database Models for InsightOps
(Merged from InsightOps and Insight projects)
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text,
    ForeignKey, Float, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from .database import Base  # Use the Base from your project's database.py

# --- Helper Functions (from Insight) ---

def _generate_uuid():
    """Generate string UUIDs for primary keys"""
    return str(uuid.uuid4())

def utc_now():
    """UTC timestamp generator"""
    return datetime.now(timezone.utc)

# --- Mixin (from Insight) ---

class TimestampMixin:
    """Adds created_at and updated_at timestamp columns to a model."""
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

# --- TaskStatus Enum (from InsightOps) ---

class TaskStatus(str, PyEnum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# --- Main Models (Merged) ---

class User(Base, TimestampMixin):
    """
    System user (from Insight)
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}')>"


class Document(Base, TimestampMixin):
    """
    Metadata for uploaded documents (Merged Model)
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

    # Status fields (from InsightOps)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True) # Renamed from metadata
    
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
    
    # Embedding info (from Insight)
    embedding_model = Column(String(100), nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    milvus_id = Column(String(100), nullable=True) # Renamed from embedding_id

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index"),
        Index("ix_chunks_doc_milvus", "document_id", "milvus_id"),
    )

    def __repr__(self):
        return f"<DocumentChunk(id='{self.id}', doc_id='{self.document_id}', idx={self.chunk_index})>"


class Task(Base, TimestampMixin):
    """
    Task tracking model for Celery (from InsightOps, with User link added)
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

    __table_args__ = (
        Index("ix_queries_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Query(id='{self.id}', user_id='{self.user_id}')>"