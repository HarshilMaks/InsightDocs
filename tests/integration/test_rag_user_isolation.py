"""
RAG query isolation tests for multi-tenant behavior.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch

from backend.api.main import app
from backend.middleware.guardrails import check_input_guardrail
from backend.models import Document, Query as QueryModel, TaskStatus
from backend.models.database import Base, get_db


engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
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
    app.dependency_overrides[check_input_guardrail] = lambda: None
    yield
    app.dependency_overrides.pop(check_input_guardrail, None)
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


def _user_id_from_token(client: TestClient, token: str) -> str:
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/users/me/byok-status", headers=h)
    assert r.status_code == 200
    return r.json()["user_id"]


class TestRAGSourceFiltering:
    def test_query_only_returns_user_sources(self, client):
        token_a = _register_and_login(client, "usera@example.com", "User A")
        token_b = _register_and_login(client, "userb@example.com", "User B")
        user_a = _user_id_from_token(client, token_a)
        user_b = _user_id_from_token(client, token_b)

        db = TestingSessionLocal()
        try:
            db.add_all(
                [
                    Document(
                        id="doc-a-1",
                        filename="a.pdf",
                        user_id=user_a,
                        status=TaskStatus.COMPLETED,
                        file_size=100,
                        file_type=".pdf",
                        s3_bucket="test",
                        s3_key="a.pdf",
                    ),
                    Document(
                        id="doc-b-1",
                        filename="b.pdf",
                        user_id=user_b,
                        status=TaskStatus.COMPLETED,
                        file_size=100,
                        file_type=".pdf",
                        s3_bucket="test",
                        s3_key="b.pdf",
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": True,
            "answer": "ok",
            "sources": [
                {"content": "A", "score": 0.95, "metadata": {"document_id": "doc-a-1"}},
                {"content": "B", "score": 0.90, "metadata": {"document_id": "doc-b-1"}},
            ],
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"query": "financial performance"},
            )

        assert r.status_code == 200, r.text
        source_ids = {s["document_id"] for s in r.json().get("sources", [])}
        assert "doc-a-1" in source_ids
        assert "doc-b-1" not in source_ids

    def test_query_with_no_user_documents_returns_empty_sources(self, client):
        token = _register_and_login(client, "empty@example.com", "Empty User")

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": True,
            "answer": "ok",
            "sources": [
                {"content": "other", "score": 0.7, "metadata": {"document_id": "non-owned-doc"}},
            ],
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "something"},
            )

        assert r.status_code == 200
        assert r.json().get("sources", []) == []

    def test_different_users_get_different_sources(self, client):
        token_a = _register_and_login(client, "diffa@example.com", "Diff A")
        token_b = _register_and_login(client, "diffb@example.com", "Diff B")
        user_a = _user_id_from_token(client, token_a)
        user_b = _user_id_from_token(client, token_b)

        db = TestingSessionLocal()
        try:
            db.add_all(
                [
                    Document(
                        id="doc-diff-a",
                        filename="da.pdf",
                        user_id=user_a,
                        status=TaskStatus.COMPLETED,
                        file_size=10,
                        file_type=".pdf",
                        s3_bucket="test",
                        s3_key="da.pdf",
                    ),
                    Document(
                        id="doc-diff-b",
                        filename="db.pdf",
                        user_id=user_b,
                        status=TaskStatus.COMPLETED,
                        file_size=10,
                        file_type=".pdf",
                        s3_bucket="test",
                        s3_key="db.pdf",
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        mock_orch = AsyncMock()

        async def _side_effect(query_text: str, user_id: str):
            if user_id == user_a:
                return {
                    "success": True,
                    "answer": "A",
                    "sources": [{"content": "A", "score": 0.8, "metadata": {"document_id": "doc-diff-a"}}],
                }
            return {
                "success": True,
                "answer": "B",
                "sources": [{"content": "B", "score": 0.8, "metadata": {"document_id": "doc-diff-b"}}],
            }

        mock_orch.process_query.side_effect = _side_effect

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            ra = client.post("/api/v1/query/", headers={"Authorization": f"Bearer {token_a}"}, json={"query": "q"})
            rb = client.post("/api/v1/query/", headers={"Authorization": f"Bearer {token_b}"}, json={"query": "q"})

        assert ra.status_code == 200 and rb.status_code == 200
        assert {s["document_id"] for s in ra.json()["sources"]} == {"doc-diff-a"}
        assert {s["document_id"] for s in rb.json()["sources"]} == {"doc-diff-b"}


class TestRAGQueryRecordTracking:
    def test_query_record_includes_user_id(self, client):
        token = _register_and_login(client, "record@example.com", "Record User")
        user_id = _user_id_from_token(client, token)

        db = TestingSessionLocal()
        try:
            db.add(
                Document(
                    id="doc-record",
                    filename="record.pdf",
                    user_id=user_id,
                    status=TaskStatus.COMPLETED,
                    file_size=10,
                    file_type=".pdf",
                    s3_bucket="test",
                    s3_key="record.pdf",
                )
            )
            db.commit()
        finally:
            db.close()

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": True,
            "answer": "ok",
            "sources": [{"content": "x", "score": 0.9, "metadata": {"document_id": "doc-record"}}],
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post("/api/v1/query/", headers={"Authorization": f"Bearer {token}"}, json={"query": "test"})

        assert r.status_code == 200
        qid = r.json()["query_id"]

        db = TestingSessionLocal()
        try:
            rec = db.query(QueryModel).filter(QueryModel.id == qid).first()
            assert rec is not None
            assert rec.user_id == user_id
        finally:
            db.close()


class TestRAGErrorHandling:
    def test_milvus_offline_returns_appropriate_error(self, client):
        token = _register_and_login(client, "errorcase@example.com", "Error Case")

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": False,
            "answer": "",
            "sources": [],
            "error": "Milvus connection failed",
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post("/api/v1/query/", headers={"Authorization": f"Bearer {token}"}, json={"query": "test"})

        assert r.status_code == 500
        assert "Milvus connection failed" in r.json().get("detail", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
