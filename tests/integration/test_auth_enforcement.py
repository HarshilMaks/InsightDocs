"""
Phase B: Authentication Enforcement Tests
Validates that all 12 protected endpoints require JWT and verify user ownership.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import os

os.environ.setdefault("JWT_SECRET", "test-secret-key")

from backend.api.main import app
from backend.models import get_db
from backend.models.schemas import User
from backend.core.security import create_access_token
from backend.models.database import engine, Base


@pytest.fixture(scope="session")
def test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    # Don't drop tables - keep for inspection


@pytest.fixture
def client(test_db):
    """FastAPI test client."""
    def override_get_db():
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def db_session(test_db):
    """Database session for test data setup."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        id="test-user-1",
        email="test@example.com",
        password_hash="hashed_password",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    """Create another test user for isolation testing."""
    user = User(
        id="test-user-2",
        email="other@example.com",
        password_hash="hashed_password",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Generate JWT token for test user."""
    return create_access_token(data={"sub": test_user.email})


@pytest.fixture
def other_auth_token(other_user):
    """Generate JWT token for other user."""
    return create_access_token(data={"sub": other_user.email})


class TestAuthenticationRequired:
    """Test that all protected endpoints return 401 without token."""

    def test_document_upload_no_token(self, client):
        """POST /documents without token → 401."""
        response = client.post("/api/v1/documents", files={"file": ("test.txt", b"content")})
        assert response.status_code == 401

    def test_document_list_no_token(self, client):
        """GET /documents without token → 401."""
        response = client.get("/api/v1/documents")
        assert response.status_code == 401

    def test_document_detail_no_token(self, client):
        """GET /documents/{id} without token → 401."""
        response = client.get("/api/v1/documents/fake-id")
        assert response.status_code == 401

    def test_document_delete_no_token(self, client):
        """DELETE /documents/{id} without token → 401."""
        response = client.delete("/api/v1/documents/fake-id")
        assert response.status_code == 401

    def test_query_no_token(self, client):
        """POST /query without token → 401."""
        response = client.post("/api/v1/query", json={"query": "test"})
        assert response.status_code == 401

    def test_task_list_no_token(self, client):
        """GET /tasks without token → 401."""
        response = client.get("/api/v1/tasks")
        assert response.status_code == 401

    def test_task_detail_no_token(self, client):
        """GET /tasks/{id} without token → 401."""
        response = client.get("/api/v1/tasks/fake-id")
        assert response.status_code == 401

    def test_summarize_no_token(self, client):
        """POST /documents/{id}/summarize without token → 401."""
        response = client.post("/api/v1/documents/fake-id/summarize")
        assert response.status_code == 401

    def test_quiz_no_token(self, client):
        """POST /documents/{id}/quiz without token → 401."""
        response = client.post("/api/v1/documents/fake-id/quiz")
        assert response.status_code == 401

    def test_mindmap_no_token(self, client):
        """POST /documents/{id}/mindmap without token → 401."""
        response = client.post("/api/v1/documents/fake-id/mindmap")
        assert response.status_code == 401

    def test_generate_podcast_no_token(self, client):
        """POST /documents/{id}/generate-podcast without token → 401."""
        response = client.post("/api/v1/documents/fake-id/generate-podcast")
        assert response.status_code == 401

    def test_get_podcast_no_token(self, client):
        """GET /documents/{id}/podcast without token → 401."""
        response = client.get("/api/v1/documents/fake-id/podcast")
        assert response.status_code == 401


class TestAuthenticationWithToken:
    """Test that protected endpoints work with valid token."""

    def test_document_list_with_token(self, client, auth_token):
        """GET /documents with token → 200."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 200
        assert "documents" in response.json()

    def test_task_list_with_token(self, client, auth_token):
        """GET /tasks with token → 200."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/tasks", headers=headers)
        assert response.status_code == 200
        assert "tasks" in response.json()


class TestUnprotectedEndpoints:
    """Test that unprotected endpoints work without token."""

    def test_root_no_token(self, client):
        """GET / without token → 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_no_token(self, client):
        """GET /health without token → 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_login_no_token(self, client):
        """POST /auth/login without token → should work."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        # May fail with wrong credentials, but shouldn't return 401
        assert response.status_code != 401

    def test_register_no_token(self, client):
        """POST /auth/register without token → should work."""
        response = client.post("/api/v1/auth/register", json={
            "email": f"newuser{hash('x')}@example.com",
            "password": "password123"
        })
        # May fail with validation, but shouldn't return 401
        assert response.status_code != 401


class TestUserIsolation:
    """Test that users can only access their own resources."""

    def test_user_sees_only_own_documents(self, client, auth_token, other_auth_token, 
                                         db_session, test_user, other_user):
        """User A's document list should not include User B's documents."""
        from backend.models import Document, TaskStatus
        
        # Create doc for user1
        doc1 = Document(
            id="doc-user1",
            filename="user1.pdf",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED,
            file_size=1000,
            chunks_count=5
        )
        db_session.add(doc1)
        db_session.commit()
        
        # Create doc for user2
        doc2 = Document(
            id="doc-user2",
            filename="user2.pdf",
            user_id=other_user.id,
            status=TaskStatus.COMPLETED,
            file_size=2000,
            chunks_count=10
        )
        db_session.add(doc2)
        db_session.commit()
        
        # User1 lists documents
        headers1 = {"Authorization": f"Bearer {auth_token}"}
        response1 = client.get("/api/v1/documents", headers=headers1)
        assert response1.status_code == 200
        docs1 = response1.json()["documents"]
        doc1_ids = [d["id"] for d in docs1]
        
        # User1 should see only their own document
        assert "doc-user1" in doc1_ids
        assert "doc-user2" not in doc1_ids
        
        # User2 lists documents
        headers2 = {"Authorization": f"Bearer {other_auth_token}"}
        response2 = client.get("/api/v1/documents", headers=headers2)
        assert response2.status_code == 200
        docs2 = response2.json()["documents"]
        doc2_ids = [d["id"] for d in docs2]
        
        # User2 should see only their own document
        assert "doc-user2" in doc2_ids
        assert "doc-user1" not in doc2_ids

    def test_user_cannot_access_others_document(self, client, auth_token, other_auth_token,
                                               db_session, test_user, other_user):
        """User A cannot GET User B's document."""
        from backend.models import Document, TaskStatus
        
        # Create doc for user2
        doc = Document(
            id="doc-other-user",
            filename="other.pdf",
            user_id=other_user.id,
            status=TaskStatus.COMPLETED,
            file_size=1000,
            chunks_count=5
        )
        db_session.add(doc)
        db_session.commit()
        
        # User1 tries to access User2's document
        headers1 = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/documents/doc-other-user", headers=headers1)
        
        # Should return 403 or 404 (not found from user's perspective)
        assert response.status_code in [403, 404]

    def test_user_cannot_delete_others_document(self, client, auth_token, other_auth_token,
                                               db_session, test_user, other_user):
        """User A cannot DELETE User B's document."""
        from backend.models import Document, TaskStatus
        
        # Create doc for user2
        doc = Document(
            id="doc-to-protect",
            filename="protected.pdf",
            user_id=other_user.id,
            status=TaskStatus.COMPLETED,
            file_size=1000,
            chunks_count=5
        )
        db_session.add(doc)
        db_session.commit()
        
        # User1 tries to delete User2's document
        headers1 = {"Authorization": f"Bearer {auth_token}"}
        response = client.delete("/api/v1/documents/doc-to-protect", headers=headers1)
        
        # Should return 403 or 404
        assert response.status_code in [403, 404]
        
        # Document should still exist for User2
        headers2 = {"Authorization": f"Bearer {other_auth_token}"}
        response2 = client.get("/api/v1/documents/doc-to-protect", headers=headers2)
        assert response2.status_code == 200
