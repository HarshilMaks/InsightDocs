"""
Database Models for InsightOps
Minimal and clean schema for users, documents, chunks, and queries
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Float, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class User(Base, TimestampMixin):
    """Basic User model"""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}')>"


class Document(Base, TimestampMixin):
    """Metadata for uploaded documents"""

    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_size = Column(Integer, nullable=False)

    s3_bucket = Column(String(100), nullable=False)
    s3_key = Column(String(500), nullable=False)

    status = Column(String(20), default="uploading", nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_user_status", "user_id", "status"),
    )

    def __repr__(self):
        return f"<Document(id='{self.id}', filename='{self.filename}', status='{self.status}')>"


class DocumentChunk(Base, TimestampMixin):
    """Chunks of document mapped to embeddings in Milvus"""

    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_model = Column(String(100), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    milvus_id = Column(String(100), nullable=True)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index"),
    )

    def __repr__(self):
        return f"<DocumentChunk(id='{self.id}', doc_id='{self.document_id}', idx={self.chunk_index})>"


class Query(Base, TimestampMixin):
    """Query logs for tracking and analytics"""

    __tablename__ = "queries"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    response_time = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=True)

    tokens_used = Column(Integer, default=0, nullable=False)
    model_name = Column(String(100), nullable=True)

    # Relationships
    user = relationship("User", back_populates="queries")

    __table_args__ = (
        Index("ix_queries_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Query(id='{self.id}', user_id='{self.user_id}')>"
