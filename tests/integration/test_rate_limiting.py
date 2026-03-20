import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from backend.api.main import app
from backend.models.database import Base, get_db
from backend.models.schemas import User


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


def test_rate_limiting_upload_enforced_per_user(client):
    token = _register_and_login(client, "ratelimit@example.com", "Rate Limit")
    headers = {"Authorization": f"Bearer {token}"}
    file_content = b"test content"

    with patch("backend.api.documents.process_document_task.apply_async") as mock_apply_async:
        mock_apply_async.return_value = type("TaskRef", (), {"id": "task-rl-1"})()

        for i in range(5):
            files = {"file": (f"test_{i}.txt", file_content, "text/plain")}
            response = client.post("/api/v1/documents/upload", files=files, headers=headers)
            assert response.status_code != 429, f"Request {i + 1} unexpectedly hit rate limit"

        files = {"file": ("test_6.txt", file_content, "text/plain")}
        response = client.post("/api/v1/documents/upload", files=files, headers=headers)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.text


def test_rate_limiting_isolated_between_users(client):
    token_a = _register_and_login(client, "ratelimit-a@example.com", "Rate A")
    token_b = _register_and_login(client, "ratelimit-b@example.com", "Rate B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    file_content = b"test content"

    with patch("backend.api.documents.process_document_task.apply_async") as mock_apply_async:
        mock_apply_async.return_value = type("TaskRef", (), {"id": "task-rl-2"})()

        for i in range(5):
            files = {"file": (f"a_{i}.txt", file_content, "text/plain")}
            assert client.post("/api/v1/documents/upload", files=files, headers=headers_a).status_code != 429

        files = {"file": ("b_0.txt", file_content, "text/plain")}
        response_b = client.post("/api/v1/documents/upload", files=files, headers=headers_b)
        assert response_b.status_code != 429
