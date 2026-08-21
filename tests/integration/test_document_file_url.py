"""Tests for the document file-url endpoint (Roadmap Phase 2, Milestone 2:
Evidence Experience — the endpoint the frontend PDF viewer depends on to
fetch the original document for citation highlighting).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock, patch

from backend.api.main import app
from backend.models import Document, TaskStatus
from backend.models.database import Base, get_db


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(setup_database):
    return TestClient(app)


def _register_and_login(client: TestClient, email: str, name: str):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "SecurePass123!"},
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "SecurePass123!"},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]["access_token"]


def _seed_document(document_id: str, user_id: str, s3_key="report.pdf", s3_bucket="insightdocs", status=TaskStatus.COMPLETED):
    db = TestingSessionLocal()
    try:
        db.add(
            Document(
                id=document_id,
                filename="report.pdf",
                file_type=".pdf",
                file_size=100,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                status=status,
                user_id=user_id,
            )
        )
        db.commit()
    finally:
        db.close()


def _user_id_from_token(client: TestClient, token: str) -> str:
    r = client.get("/api/v1/users/me/byok-status", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


class TestDocumentFileUrlEndpoint:
    def test_owner_receives_a_presigned_url(self, client):
        token = _register_and_login(client, "owner@example.com", "Owner")
        user_id = _user_id_from_token(client, token)
        _seed_document("doc-file-1", user_id)

        fake_storage = MagicMock()
        fake_storage.get_file_url.return_value = "https://minio.local/insightdocs/report.pdf?sig=abc"

        with patch("backend.storage.file_storage.FileStorage", return_value=fake_storage):
            r = client.get(
                "/api/v1/documents/doc-file-1/file-url",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["document_id"] == "doc-file-1"
        assert payload["url"] == "https://minio.local/insightdocs/report.pdf?sig=abc"
        assert payload["expires_in"] == 600
        fake_storage.get_file_url.assert_called_once_with("report.pdf", expires_in=600)

    def test_non_owner_cannot_access_another_users_file_url(self, client):
        owner_token = _register_and_login(client, "owner2@example.com", "Owner Two")
        owner_id = _user_id_from_token(client, owner_token)
        _seed_document("doc-file-2", owner_id)

        other_token = _register_and_login(client, "intruder@example.com", "Intruder")

        r = client.get(
            "/api/v1/documents/doc-file-2/file-url",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert r.status_code == 404

    def test_unauthenticated_request_is_rejected(self, client):
        r = client.get("/api/v1/documents/doc-file-3/file-url")
        assert r.status_code == 401

    def test_document_without_stored_file_returns_409(self, client):
        token = _register_and_login(client, "pending@example.com", "Pending User")
        user_id = _user_id_from_token(client, token)
        # s3_key/s3_bucket are NOT NULL columns (always set at upload time
        # per the Phase 0 upload flow), so an empty string is the realistic
        # way to represent "no file stored yet" without violating the
        # schema's own constraints.
        _seed_document("doc-file-4", user_id, s3_key="", s3_bucket="", status=TaskStatus.PENDING)

        r = client.get(
            "/api/v1/documents/doc-file-4/file-url",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 409


class TestDocumentDeletion:
    def test_owner_deletion_removes_vectors_and_source_object(self, client):
        token = _register_and_login(client, "delete-owner@example.com", "Delete Owner")
        user_id = _user_id_from_token(client, token)
        _seed_document("doc-delete-1", user_id, s3_key="documents/delete-me.pdf")

        fake_storage = MagicMock()
        fake_storage.delete_file = AsyncMock(return_value=True)
        fake_embeddings = MagicMock()
        fake_embeddings.delete_document_vectors = AsyncMock()

        with patch("backend.storage.file_storage.FileStorage", return_value=fake_storage), patch(
            "backend.utils.embeddings.get_embedding_engine", return_value=fake_embeddings
        ):
            response = client.delete(
                "/api/v1/documents/doc-delete-1",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200, response.text
        fake_embeddings.delete_document_vectors.assert_awaited_once_with("doc-delete-1", user_id)
        fake_storage.delete_file.assert_awaited_once_with("documents/delete-me.pdf")

        db = TestingSessionLocal()
        try:
            assert db.query(Document).filter(Document.id == "doc-delete-1").first() is None
        finally:
            db.close()

    def test_pending_document_can_be_deleted_when_no_worker_has_started(self, client):
        token = _register_and_login(client, "delete-pending@example.com", "Delete Pending")
        user_id = _user_id_from_token(client, token)
        _seed_document(
            "doc-delete-pending",
            user_id,
            s3_key="documents/pending.pdf",
            status=TaskStatus.PENDING,
        )

        fake_embeddings = MagicMock()
        fake_embeddings.delete_document_vectors = AsyncMock()
        fake_storage = MagicMock()
        fake_storage.delete_file = AsyncMock(return_value=True)
        with patch("backend.utils.embeddings.get_embedding_engine", return_value=fake_embeddings), patch(
            "backend.storage.file_storage.FileStorage", return_value=fake_storage
        ):
            response = client.delete(
                "/api/v1/documents/doc-delete-pending",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200, response.text
        fake_embeddings.delete_document_vectors.assert_awaited_once_with("doc-delete-pending", user_id)
        fake_storage.delete_file.assert_awaited_once_with("documents/pending.pdf")

    def test_index_cleanup_failure_preserves_document_record(self, client):
        token = _register_and_login(client, "delete-failure@example.com", "Delete Failure")
        user_id = _user_id_from_token(client, token)
        _seed_document("doc-delete-2", user_id, s3_key="documents/retain-me.pdf")

        fake_embeddings = MagicMock()
        fake_embeddings.delete_document_vectors = AsyncMock(side_effect=RuntimeError("Milvus unavailable"))

        with patch("backend.utils.embeddings.get_embedding_engine", return_value=fake_embeddings):
            response = client.delete(
                "/api/v1/documents/doc-delete-2",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 503
        db = TestingSessionLocal()
        try:
            assert db.query(Document).filter(Document.id == "doc-delete-2").first() is not None
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
