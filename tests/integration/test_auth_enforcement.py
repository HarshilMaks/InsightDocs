"""
Authentication enforcement and resource isolation tests.
Uses in-memory SQLite and current API contracts.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.models import Document, Task, TaskStatus
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


class TestAuthenticationRequired:
    def test_documents_upload_no_token(self, client):
        r = client.post("/api/v1/documents/upload", files={"file": ("a.txt", b"x")})
        assert r.status_code == 401

    def test_documents_list_no_token(self, client):
        r = client.get("/api/v1/documents/")
        assert r.status_code == 401

    def test_documents_detail_no_token(self, client):
        r = client.get("/api/v1/documents/fake-id")
        assert r.status_code == 401

    def test_documents_delete_no_token(self, client):
        r = client.delete("/api/v1/documents/fake-id")
        assert r.status_code == 401

    def test_query_no_token(self, client):
        r = client.post("/api/v1/query/", json={"query": "test"})
        assert r.status_code == 401

    def test_tasks_list_no_token(self, client):
        r = client.get("/api/v1/tasks/")
        assert r.status_code == 401

    def test_tasks_detail_no_token(self, client):
        r = client.get("/api/v1/tasks/fake-id")
        assert r.status_code == 401

    def test_summarize_no_token(self, client):
        r = client.post("/api/v1/documents/fake-id/summarize")
        assert r.status_code == 401

    def test_quiz_no_token(self, client):
        r = client.post("/api/v1/documents/fake-id/quiz")
        assert r.status_code == 401

    def test_mindmap_no_token(self, client):
        r = client.post("/api/v1/documents/fake-id/mindmap")
        assert r.status_code == 401

    def test_generate_podcast_no_token(self, client):
        r = client.post("/api/v1/documents/fake-id/generate-podcast")
        assert r.status_code == 401

    def test_get_podcast_no_token(self, client):
        r = client.get("/api/v1/documents/fake-id/podcast")
        assert r.status_code == 401


class TestProtectedEndpointsWithToken:
    def test_documents_list_with_token(self, client):
        token = _register_and_login(client, "authlist@example.com", "Auth List")
        r = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "documents" in r.json()

    def test_tasks_list_with_token(self, client):
        token = _register_and_login(client, "authtask@example.com", "Auth Task")
        r = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "tasks" in r.json()


class TestUnprotectedEndpoints:
    def test_root_no_token(self, client):
        assert client.get("/").status_code == 200

    def test_health_no_token(self, client):
        assert client.get("/api/v1/health").status_code == 200

    def test_register_no_token(self, client):
        r = client.post(
            "/api/v1/auth/register",
            json={"email": "openreg@example.com", "name": "Open", "password": "SecurePass123!"},
        )
        assert r.status_code in (201, 400)


class TestUserIsolation:
    def test_user_sees_only_own_documents(self, client):
        token1 = _register_and_login(client, "iso1@example.com", "Iso One")
        token2 = _register_and_login(client, "iso2@example.com", "Iso Two")

        h1 = {"Authorization": f"Bearer {token1}"}
        h2 = {"Authorization": f"Bearer {token2}"}

        u1 = client.get("/api/v1/users/me/byok-status", headers=h1).json()["user_id"]
        u2 = client.get("/api/v1/users/me/byok-status", headers=h2).json()["user_id"]

        db = TestingSessionLocal()
        try:
            db.add_all(
                [
                    Document(
                        id="iso-doc-1",
                        filename="u1.pdf",
                        user_id=u1,
                        status=TaskStatus.COMPLETED,
                        file_size=10,
                        file_type=".pdf",
                        s3_bucket="b",
                        s3_key="k1",
                    ),
                    Document(
                        id="iso-doc-2",
                        filename="u2.pdf",
                        user_id=u2,
                        status=TaskStatus.COMPLETED,
                        file_size=10,
                        file_type=".pdf",
                        s3_bucket="b",
                        s3_key="k2",
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        r1 = client.get("/api/v1/documents/", headers=h1)
        r2 = client.get("/api/v1/documents/", headers=h2)

        ids1 = {d["id"] for d in r1.json()["documents"]}
        ids2 = {d["id"] for d in r2.json()["documents"]}

        assert "iso-doc-1" in ids1 and "iso-doc-2" not in ids1
        assert "iso-doc-2" in ids2 and "iso-doc-1" not in ids2

    def test_user_cannot_access_others_document(self, client):
        token1 = _register_and_login(client, "iso3@example.com", "Iso Three")
        token2 = _register_and_login(client, "iso4@example.com", "Iso Four")
        h1 = {"Authorization": f"Bearer {token1}"}
        h2 = {"Authorization": f"Bearer {token2}"}

        u2 = client.get("/api/v1/users/me/byok-status", headers=h2).json()["user_id"]

        db = TestingSessionLocal()
        try:
            db.add(
                Document(
                    id="iso-protected-doc",
                    filename="protected.pdf",
                    user_id=u2,
                    status=TaskStatus.COMPLETED,
                    file_size=10,
                    file_type=".pdf",
                    s3_bucket="b",
                    s3_key="k3",
                )
            )
            db.commit()
        finally:
            db.close()

        r = client.get("/api/v1/documents/iso-protected-doc", headers=h1)
        assert r.status_code == 404

    def test_user_cannot_delete_others_document(self, client):
        token1 = _register_and_login(client, "iso5@example.com", "Iso Five")
        token2 = _register_and_login(client, "iso6@example.com", "Iso Six")
        h1 = {"Authorization": f"Bearer {token1}"}
        h2 = {"Authorization": f"Bearer {token2}"}

        u2 = client.get("/api/v1/users/me/byok-status", headers=h2).json()["user_id"]

        db = TestingSessionLocal()
        try:
            db.add(
                Document(
                    id="iso-delete-doc",
                    filename="protected2.pdf",
                    user_id=u2,
                    status=TaskStatus.COMPLETED,
                    file_size=10,
                    file_type=".pdf",
                    s3_bucket="b",
                    s3_key="k4",
                )
            )
            db.commit()
        finally:
            db.close()

        r = client.delete("/api/v1/documents/iso-delete-doc", headers=h1)
        assert r.status_code == 404

        r2 = client.get("/api/v1/documents/iso-delete-doc", headers=h2)
        assert r2.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
