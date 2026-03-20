"""
Integration tests for tenant isolation in API and Milvus search filtering.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, patch

from backend.api.main import app
from backend.models import Document, TaskStatus
from backend.models.database import Base, get_db
from backend.middleware.guardrails import check_input_guardrail


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


class TestTenantIsolation:
    def test_document_list_isolation(self, client):
        token1 = _register_and_login(client, "tenant1@example.com", "Tenant One")
        token2 = _register_and_login(client, "tenant2@example.com", "Tenant Two")

        h1 = {"Authorization": f"Bearer {token1}"}
        h2 = {"Authorization": f"Bearer {token2}"}

        db = TestingSessionLocal()
        try:
            # derive user IDs from auth status endpoint
            u1 = client.get("/api/v1/users/me/byok-status", headers=h1).json()["user_id"]
            u2 = client.get("/api/v1/users/me/byok-status", headers=h2).json()["user_id"]

            d1 = Document(
                id="doc-user1",
                filename="user1.pdf",
                file_type=".pdf",
                file_size=111,
                s3_bucket="test",
                s3_key="a.pdf",
                status=TaskStatus.COMPLETED,
                user_id=u1,
            )
            d2 = Document(
                id="doc-user2",
                filename="user2.pdf",
                file_type=".pdf",
                file_size=222,
                s3_bucket="test",
                s3_key="b.pdf",
                status=TaskStatus.COMPLETED,
                user_id=u2,
            )
            db.add_all([d1, d2])
            db.commit()
        finally:
            db.close()

        r1 = client.get("/api/v1/documents/", headers=h1)
        r2 = client.get("/api/v1/documents/", headers=h2)

        assert r1.status_code == 200
        assert r2.status_code == 200

        ids1 = {d["id"] for d in r1.json()["documents"]}
        ids2 = {d["id"] for d in r2.json()["documents"]}

        assert "doc-user1" in ids1 and "doc-user2" not in ids1
        assert "doc-user2" in ids2 and "doc-user1" not in ids2

    @pytest.mark.asyncio
    async def test_query_passes_user_id_to_orchestrator(self, client):
        token = _register_and_login(client, "querytenant@example.com", "Query Tenant")
        headers = {"Authorization": f"Bearer {token}"}

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_query.return_value = {
            "success": True,
            "answer": "ok",
            "sources": [],
        }
        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orchestrator):
            r = client.post("/api/v1/query/", json={"query": "hello"}, headers=headers)
            assert r.status_code == 200, r.text
            assert mock_orchestrator.process_query.await_count == 1
            _, kwargs = mock_orchestrator.process_query.await_args
            assert "user_id" in kwargs and kwargs["user_id"]

    @pytest.mark.asyncio
    async def test_query_source_filter_ownership(self, client):
        token1 = _register_and_login(client, "srca@example.com", "Src A")
        token2 = _register_and_login(client, "srcb@example.com", "Src B")

        h1 = {"Authorization": f"Bearer {token1}"}
        h2 = {"Authorization": f"Bearer {token2}"}

        s1 = client.get("/api/v1/users/me/byok-status", headers=h1).json()
        s2 = client.get("/api/v1/users/me/byok-status", headers=h2).json()
        u1 = s1["user_id"]
        u2 = s2["user_id"]

        db = TestingSessionLocal()
        try:
            db.add_all(
                [
                    Document(
                        id="doc-src-1",
                        filename="src1.pdf",
                        file_type=".pdf",
                        file_size=100,
                        s3_bucket="test",
                        s3_key="src1.pdf",
                        status=TaskStatus.COMPLETED,
                        user_id=u1,
                    ),
                    Document(
                        id="doc-src-2",
                        filename="src2.pdf",
                        file_type=".pdf",
                        file_size=100,
                        s3_bucket="test",
                        s3_key="src2.pdf",
                        status=TaskStatus.COMPLETED,
                        user_id=u2,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_query.return_value = {
            "success": True,
            "answer": "ok",
            "sources": [
                {"content": "own", "score": 0.9, "metadata": {"document_id": "doc-src-1"}},
                {"content": "other", "score": 0.8, "metadata": {"document_id": "doc-src-2"}},
            ],
        }
        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orchestrator):
            r = client.post("/api/v1/query/", json={"query": "x"}, headers=h1)
            assert r.status_code == 200, r.text
            src_ids = {s["document_id"] for s in r.json()["sources"]}
            assert "doc-src-1" in src_ids
            assert "doc-src-2" not in src_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
