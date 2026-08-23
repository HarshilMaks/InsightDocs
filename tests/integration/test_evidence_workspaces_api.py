"""Integration coverage for private multi-document Evidence Workspaces."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.core.limiter import limiter
from backend.middleware.guardrails import check_input_guardrail
from backend.models import Base, Document, Query, TaskStatus
from backend.models.database import get_db


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
    limiter.reset()
    return TestClient(app)


def _register_and_login(client: TestClient, email: str, name: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "SecurePass123!"},
    )
    assert response.status_code == 201, response.text
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "SecurePass123!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]["access_token"]


def _user_id(client: TestClient, token: str) -> str:
    response = client.get("/api/v1/users/me/byok-status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    return response.json()["user_id"]


def _seed_document(document_id: str, user_id: str, status: TaskStatus = TaskStatus.COMPLETED):
    db = TestingSessionLocal()
    try:
        db.add(
            Document(
                id=document_id,
                filename=f"{document_id}.pdf",
                file_type=".pdf",
                file_size=100,
                s3_bucket="test",
                s3_key=f"documents/{document_id}.pdf",
                status=status,
                user_id=user_id,
            )
        )
        db.commit()
    finally:
        db.close()


def test_workspace_crud_membership_and_owner_isolation(client):
    owner_token = _register_and_login(client, "workspace-owner@example.com", "Workspace Owner")
    other_token = _register_and_login(client, "workspace-other@example.com", "Workspace Other")
    owner_id = _user_id(client, owner_token)
    other_id = _user_id(client, other_token)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    _seed_document("workspace-doc-a", owner_id)
    _seed_document("workspace-doc-b", owner_id)
    _seed_document("workspace-other-doc", other_id)

    created = client.post(
        "/api/v1/workspaces",
        headers=owner_headers,
        json={
            "name": "Vendor review",
            "description": "Compare selected security evidence.",
            "document_ids": ["workspace-doc-a", "workspace-doc-b", "workspace-doc-a"],
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    workspace_id = payload["id"]
    assert payload["document_count"] == 2
    assert [document["id"] for document in payload["documents"]] == [
        "workspace-doc-a",
        "workspace-doc-b",
    ]

    listed = client.get("/api/v1/workspaces", headers=owner_headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["workspaces"][0]["document_count"] == 2

    assert client.get(f"/api/v1/workspaces/{workspace_id}", headers=other_headers).status_code == 404
    assert (
        client.put(
            f"/api/v1/workspaces/{workspace_id}/documents/workspace-other-doc",
            headers=owner_headers,
        ).status_code
        == 404
    )

    # Re-adding an existing document is idempotent and does not duplicate the corpus.
    same_document = client.put(
        f"/api/v1/workspaces/{workspace_id}/documents/workspace-doc-a",
        headers=owner_headers,
    )
    assert same_document.status_code == 200, same_document.text
    assert same_document.json()["document_count"] == 2

    removed = client.delete(
        f"/api/v1/workspaces/{workspace_id}/documents/workspace-doc-b",
        headers=owner_headers,
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["document_count"] == 1


def test_workspace_query_uses_only_selected_ready_documents_and_records_provenance(client):
    token = _register_and_login(client, "workspace-query@example.com", "Workspace Query")
    user_id = _user_id(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    _seed_document("workspace-query-ready", user_id)
    _seed_document("workspace-query-pending", user_id, status=TaskStatus.PENDING)

    workspace = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "name": "Selected corpus",
            "document_ids": ["workspace-query-ready", "workspace-query-pending"],
        },
    )
    assert workspace.status_code == 201, workspace.text
    workspace_id = workspace.json()["id"]

    fake_orchestrator = MagicMock()
    fake_orchestrator.process_query = AsyncMock(
        return_value={
            "success": True,
            "answer": "Evidence-grounded answer.",
            "sources": [],
            "claim_verifications": None,
        }
    )
    with patch("backend.api.query._get_user_orchestrator", return_value=fake_orchestrator):
        response = client.post(
            "/api/v1/query/",
            headers=headers,
            json={"query": "What does the selected corpus say?", "workspace_id": workspace_id},
        )

    assert response.status_code == 200, response.text
    assert fake_orchestrator.process_query.await_args.kwargs["document_ids"] == ["workspace-query-ready"]
    assert fake_orchestrator.process_query.await_args.kwargs["document_id"] is None

    db = TestingSessionLocal()
    try:
        query = db.query(Query).filter(Query.id == response.json()["query_id"]).one()
        assert query.workspace_id == workspace_id
    finally:
        db.close()

    ambiguous = client.post(
        "/api/v1/query/",
        headers=headers,
        json={
            "query": "This must be rejected.",
            "workspace_id": workspace_id,
            "document_id": "workspace-query-ready",
        },
    )
    assert ambiguous.status_code == 422


def test_empty_workspace_query_never_falls_back_to_full_library(client):
    token = _register_and_login(client, "workspace-empty@example.com", "Workspace Empty")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={"name": "Empty corpus"},
    )
    assert workspace.status_code == 201, workspace.text

    response = client.post(
        "/api/v1/query/",
        headers=headers,
        json={"query": "Should not search everything.", "workspace_id": workspace.json()["id"]},
    )
    assert response.status_code == 400
    assert "no ready documents" in response.json()["detail"].lower()
