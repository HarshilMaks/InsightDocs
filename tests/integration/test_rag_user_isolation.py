"""
Phase B: RAG Query and User Isolation Tests
Tests that RAG searches only return results from current user's documents.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock

os.environ.setdefault("JWT_SECRET", "test-secret-key")

from fastapi.testclient import TestClient
from backend.api.main import app
from backend.models import get_db, Document, DocumentChunk, TaskStatus
from backend.models.schemas import User
from backend.core.security import create_access_token
from backend.models.database import engine, Base


@pytest.fixture(scope="function")
def test_db_engine():
    """Create in-memory SQLite engine."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def test_db(test_db_engine):
    """Ensure tables exist."""
    yield

@pytest.fixture
def db_session(test_db_engine):
    """Database session."""
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(test_db_engine):
    """FastAPI test client."""
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides = {}


@pytest.fixture
def user_a(db_session):
    """Create test user A."""
    user = User(
        id="user-a",
        email="usera@example.com",
        name="User A",
        hashed_password="hash",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def user_b(db_session):
    """Create test user B."""
    user = User(
        id="user-b",
        email="userb@example.com",
        name="User B",
        hashed_password="hash",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def token_a(user_a):
    """JWT token for user A."""
    return create_access_token(data={"user_id": user_a.id, "sub": user_a.email})


@pytest.fixture
def token_b(user_b):
    """JWT token for user B."""
    return create_access_token(data={"user_id": user_b.id, "sub": user_b.email})


@pytest.fixture
def user_a_docs(db_session, user_a):
    """Create documents for user A."""
    doc = Document(
        id="doc-a-1",
        filename="financial_report.pdf",
        user_id=user_a.id,
        status=TaskStatus.COMPLETED,
        file_size=5000,
        file_type="application/pdf",
        s3_bucket="test-bucket",
        s3_key="uploads/financial_report.pdf",
    )
    db_session.add(doc)
    
    # Add chunks with searchable content
    chunk = DocumentChunk(
        id="chunk-a-1",
        document_id="doc-a-1",
        content="Our quarterly financial performance shows strong growth in revenue.",
        chunk_index=0
    )
    db_session.add(chunk)
    db_session.commit()
    
    return [doc]


@pytest.fixture
def user_b_docs(db_session, user_b):
    """Create documents for user B."""
    doc = Document(
        id="doc-b-1",
        filename="marketing_strategy.pdf",
        user_id=user_b.id,
        status=TaskStatus.COMPLETED,
        file_size=3000,
        file_type="application/pdf",
        s3_bucket="test-bucket",
        s3_key="uploads/marketing_strategy.pdf",
    )
    db_session.add(doc)
    
    # Add chunks with different content
    chunk = DocumentChunk(
        id="chunk-b-1",
        document_id="doc-b-1",
        content="Our marketing strategy focuses on customer engagement and brand awareness.",
        chunk_index=0
    )
    db_session.add(chunk)
    db_session.commit()
    
    return [doc]

@pytest.fixture
def mock_rag_components():
    """Mock all external RAG components to prevent real API/Model calls."""
    with patch('backend.middleware.guardrails._call_gemini_guard', return_value=(True, "")) as mock_guard, \
         patch('backend.api.query.get_embedding_engine') as mock_get_engine, \
         patch('backend.api.query.get_reranker') as mock_get_reranker, \
         patch('backend.api.query.LLMClient') as mock_llm_cls:
        
        # Mock Embedding Engine
        mock_engine = MagicMock()
        mock_engine.search = AsyncMock()  # Async search
        mock_get_engine.return_value = mock_engine
        
        # Mock Reranker
        mock_reranker = MagicMock()
        # Default behavior: return results as-is (sliced by top_n)
        mock_reranker.rerank.side_effect = lambda q, r, top_n=5: r[:top_n]
        mock_get_reranker.return_value = mock_reranker
        
        # Mock LLM Client
        mock_llm = MagicMock()
        mock_llm.generate_rag_response = AsyncMock(return_value="Mocked RAG response") # Async generate
        mock_llm_cls.return_value = mock_llm
        
        yield {
            "guard": mock_guard,
            "engine": mock_engine,
            "reranker": mock_reranker,
            "llm": mock_llm
        }


class TestRAGSourceFiltering:
    """Test that RAG results are filtered by user ownership."""

    def test_query_only_returns_user_sources(self, client, token_a, user_a_docs, user_b_docs, mock_rag_components):
        """User A's query should only return sources from User A's documents."""
        headers = {"Authorization": f"Bearer {token_a}"}
        
        # Mock embedding search returning results from both users
        mock_rag_components["engine"].search.return_value = [
            {
                "text": "Revenue data...",
                "metadata": {"document_id": "doc-a-1"},
                "score": 0.95
            },
            {
                "text": "Marketing campaign...",
                "metadata": {"document_id": "doc-b-1"},
                "score": 0.87
            }
        ]
        
        response = client.post(
            "/api/v1/query/",
            headers=headers,
            json={"query": "financial performance"}
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Should only include User A's sources
        source_ids = [s["document_id"] for s in result.get("sources", [])]
        assert "doc-a-1" in source_ids
        assert "doc-b-1" not in source_ids

    def test_query_with_no_user_documents_returns_empty_sources(self, client, token_b, mock_rag_components):
        """User with no documents should get empty sources."""
        headers = {"Authorization": f"Bearer {token_b}"}
        
        # Mock engine returns some results (e.g. from other users)
        mock_rag_components["engine"].search.return_value = [
             {
                "text": "Revenue data...",
                "metadata": {"document_id": "doc-a-1"},
                "score": 0.95
            }
        ]
        
        # This user (B) has no documents yet (if we don't use user_b_docs fixture)
        
        response = client.post(
            "/api/v1/query/",
            headers=headers,
            json={"query": "something to search"}
        )
        
        assert response.status_code == 200
        result = response.json()
        # User has no documents, so sources should be empty
        assert len(result.get("sources", [])) == 0

    def test_different_users_get_different_sources(self, client, token_a, token_b,
                                                  user_a_docs, user_b_docs, mock_rag_components):
        """User A and User B should get different sources for same query."""
        
        # Mock returns all results
        mock_rag_components["engine"].search.return_value = [
            {
                "text": "User A's content",
                "metadata": {"document_id": "doc-a-1"},
                "score": 0.9
            },
            {
                "text": "User B's content",
                "metadata": {"document_id": "doc-b-1"},
                "score": 0.85
            }
        ]
        
        # User A searches
        headers_a = {"Authorization": f"Bearer {token_a}"}
        response_a = client.post(
            "/api/v1/query/",
            headers=headers_a,
            json={"query": "content"}
        )
        sources_a = response_a.json().get("sources", [])
        
        # User B searches same query
        headers_b = {"Authorization": f"Bearer {token_b}"}
        response_b = client.post(
            "/api/v1/query/",
            headers=headers_b,
            json={"query": "content"}
        )
        sources_b = response_b.json().get("sources", [])
        
        # Results should differ based on user ownership
        doc_ids_a = {s.get("document_id") for s in sources_a}
        doc_ids_b = {s.get("document_id") for s in sources_b}
        
        assert "doc-a-1" in doc_ids_a
        assert "doc-b-1" not in doc_ids_a
        
        assert "doc-b-1" in doc_ids_b
        assert "doc-a-1" not in doc_ids_b


class TestRAGQueryRecordTracking:
    """Test that query records include user information."""

    def test_query_record_includes_user_id(self, db_session, client, token_a, mock_rag_components):
        """Query record in database should include user_id."""
        headers = {"Authorization": f"Bearer {token_a}"}
        
        mock_rag_components["engine"].search.return_value = [
            {
                "text": "test result",
                "metadata": {"document_id": "doc-a-1"},
                "score": 0.9
            }
        ]
        
        response = client.post(
            "/api/v1/query/",
            headers=headers,
            json={"query": "test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "query_id" in data
        
        # Verify in DB
        from backend.models import Query as QueryModel
        query_record = db_session.query(QueryModel).filter_by(id=data["query_id"]).first()
        assert query_record is not None
        assert query_record.user_id == "user-a"


class TestRAGWithOCRContent:
    """Test RAG search on OCR-extracted content."""

    def test_query_finds_ocr_extracted_text(self, db_session, client, token_a, mock_rag_components):
        """RAG should search OCR-extracted text effectively."""
        
        # Create document with OCR metadata
        doc = Document(
            id="ocr-doc",
            filename="scanned.pdf",
            user_id="user-a",
            status=TaskStatus.COMPLETED,
            file_size=2000,
            file_type="application/pdf",
            s3_bucket="test-bucket",
            s3_key="uploads/scanned.pdf",
            is_scanned=True,
            ocr_confidence=0.92
        )
        db_session.add(doc)
        db_session.commit()
        
        headers = {"Authorization": f"Bearer {token_a}"}
        
        mock_rag_components["engine"].search.return_value = [
            {
                "text": "This text was extracted from a scanned document...",
                "metadata": {"document_id": "ocr-doc"},
                "score": 0.88
            }
        ]
        
        response = client.post(
            "/api/v1/query/",
            headers=headers,
            json={"query": "scanned document OCR"}
        )
        
        assert response.status_code == 200
        sources = response.json().get("sources", [])
        assert len(sources) > 0
        assert sources[0]["document_id"] == "ocr-doc"


class TestRAGErrorHandling:
    """Test RAG query error handling."""

    def test_empty_query_handled(self, client, token_a, mock_rag_components):
        """Empty query should be handled gracefully."""
        headers = {"Authorization": f"Bearer {token_a}"}
        
        response = client.post(
            "/api/v1/query/",
            headers=headers,
            json={"query": ""}
        )
        
        # Should either succeed with empty results or return 400
        # If the backend allows empty query strings
        assert response.status_code in [200, 400]

    def test_milvus_offline_returns_appropriate_error(self, client, token_a, mock_rag_components):
        """If Milvus is offline, should return appropriate error."""
        headers = {"Authorization": f"Bearer {token_a}"}
        
        # Simulate engine failure
        mock_rag_components["engine"].search.side_effect = Exception("Milvus connection failed")
        
        response = client.post(
            "/api/v1/query/",
            headers=headers,
            json={"query": "test"}
        )
        
        # Should return 500
        assert response.status_code == 500
        assert "Milvus connection failed" in response.json().get("detail", "")
