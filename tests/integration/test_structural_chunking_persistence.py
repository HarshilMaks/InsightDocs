"""Tests for persisting section-aware, table-atomic, parent-child chunks
to PostgreSQL (Roadmap Phase 1, Milestone 1).

Verifies that OrchestratorAgent._store_chunks_to_db resolves in-memory
parent_chunk_index references to real DocumentChunk row ids, since parent
chunks must be inserted before their children can reference them via the
parent_chunk_id foreign key.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from backend.agents.orchestrator import OrchestratorAgent
from backend.models.database import Base
from backend.models import Document, DocumentChunk, TaskStatus


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _seed_document(document_id: str):
    db = TestingSessionLocal()
    try:
        db.add(
            Document(
                id=document_id,
                filename="structured.pdf",
                file_type=".pdf",
                file_size=100,
                s3_bucket="bucket",
                s3_key="structured.pdf",
                status=TaskStatus.PROCESSING,
                user_id="user-1",
            )
        )
        db.commit()
    finally:
        db.close()


def _fake_get_db():
    """Mimic backend.models.get_db()'s generator contract (supports
    .close() via GeneratorExit) using a real test session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.mark.asyncio
async def test_store_chunks_resolves_parent_index_to_real_db_id():
    document_id = "doc-structural-1"
    _seed_document(document_id)

    chunks = [
        {
            "text": "Security Policy",
            "page_number": 1,
            "bbox": {"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 10.0},
            "chunk_type": "text",
            "section_title": "Security Policy",
            "parent_chunk_index": None,
            "is_parent": True,
        },
        {
            "text": "All access must be authenticated.",
            "page_number": 1,
            "bbox": {"x1": 0.0, "y1": 10.0, "x2": 100.0, "y2": 20.0},
            "chunk_type": "text",
            "section_title": "Security Policy",
            "parent_chunk_index": 0,
        },
        {
            "text": "| Col1 | Col2 |\n| --- | --- |\n| a | b |",
            "page_number": 1,
            "bbox": {"x1": 0.0, "y1": 20.0, "x2": 100.0, "y2": 30.0},
            "chunk_type": "table",
            "section_title": "Security Policy",
            "parent_chunk_index": None,
        },
    ]
    vector_ids = ["vec-parent", "vec-child", "vec-table"]

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)  # bypass __init__ side effects

    with patch("backend.models.get_db", side_effect=_fake_get_db):
        await orchestrator._store_chunks_to_db(document_id, chunks, vector_ids)

    db = TestingSessionLocal()
    try:
        rows = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        assert len(rows) == 3

        parent_row = next(r for r in rows if r.chunk_index == 0)
        child_row = next(r for r in rows if r.chunk_index == 1)
        table_row = next(r for r in rows if r.chunk_index == 2)

        assert parent_row.section_title == "Security Policy"
        assert parent_row.parent_chunk_id is None

        # The child's parent_chunk_id must resolve to the parent's real
        # primary key, not the in-memory list position (0).
        assert child_row.parent_chunk_id == parent_row.id
        assert child_row.parent_chunk_id != "0"

        assert table_row.chunk_type == "table"
        assert table_row.parent_chunk_id is None
        assert "Col1" in table_row.content
    finally:
        db.close()


@pytest.mark.asyncio
async def test_store_chunks_still_works_for_legacy_string_chunks():
    """Backward compatibility: chunks produced by the plain-text fallback
    path (list of raw strings) must still persist correctly with the new
    columns defaulting to sensible values."""
    document_id = "doc-legacy-1"
    _seed_document(document_id)

    chunks = ["Just a plain string chunk with no structure."]
    vector_ids = ["vec-legacy-1"]

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)

    with patch("backend.models.get_db", side_effect=_fake_get_db):
        await orchestrator._store_chunks_to_db(document_id, chunks, vector_ids)

    db = TestingSessionLocal()
    try:
        row = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).first()
        assert row is not None
        assert row.content == "Just a plain string chunk with no structure."
        assert row.section_title is None
        assert row.parent_chunk_id is None
        assert row.chunk_type == "text"
    finally:
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
