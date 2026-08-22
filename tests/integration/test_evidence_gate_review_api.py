from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.core.limiter import limiter
from backend.models import (
    Base,
    Document,
    EvidenceGateClaim,
    EvidenceGateRun,
    Query,
    TaskStatus,
)
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
    yield
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
    response = client.get(
        "/api/v1/users/me/byok-status", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    return response.json()["user_id"]


def _seed_review_run(owner_id: str, other_id: str) -> str:
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                Document(
                    id="review-owner-document",
                    filename="owner.pdf",
                    file_type=".pdf",
                    file_size=100,
                    s3_bucket="test",
                    s3_key="owner.pdf",
                    status=TaskStatus.COMPLETED,
                    user_id=owner_id,
                ),
                Document(
                    id="review-other-document",
                    filename="other.pdf",
                    file_type=".pdf",
                    file_size=100,
                    s3_bucket="test",
                    s3_key="other.pdf",
                    status=TaskStatus.COMPLETED,
                    user_id=other_id,
                ),
            ]
        )
        query = Query(
            id="review-query",
            user_id=owner_id,
            query_text="What does the owner document say?",
            response_text="It records the owner evidence.",
            sources=[
                {
                    "content": "Owner evidence snapshot.",
                    "score": 0.97,
                    "metadata": {
                        "document_id": "review-owner-document",
                        "citation": {
                            "source_number": 1,
                            "document_id": "review-owner-document",
                            "chunk_id": "owner-chunk",
                            "chunk_index": 3,
                            "page_number": 2,
                            "bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
                            "section_title": "Owner section",
                            "chunk_type": "text",
                            "citation_label": "owner citation",
                        },
                    },
                },
                {
                    "content": "Cross-tenant snapshot that must not be disclosed.",
                    "score": 0.88,
                    "metadata": {
                        "document_id": "review-other-document",
                        "citation": {
                            "source_number": 2,
                            "document_id": "review-other-document",
                            "chunk_id": "other-chunk",
                            "chunk_index": 1,
                        },
                    },
                },
            ],
        )
        run = EvidenceGateRun(
            id="review-run",
            query=query,
            user_id=owner_id,
            attempt=1,
            policy_version="evidence-gate/v1",
            mode="shadow",
            status="failed",
            action="annotate",
            candidate_answer_sha256="a" * 64,
            delivered_answer_sha256="a" * 64,
            source_snapshot_sha256="b" * 64,
            claim_count=1,
            unsupported_count=1,
        )
        claim = EvidenceGateClaim(
            gate_run=run,
            ordinal=1,
            claim_text="It records the owner evidence.",
            claim_sha256="c" * 64,
            verdict="unsupported",
            reason="Needs reviewer confirmation.",
            supporting_source_numbers=[1, 2],
        )
        db.add_all([query, run, claim])
        db.commit()
        return run.id
    finally:
        db.close()


def test_owner_scoped_review_queue_detail_decisions_and_history(client):
    owner_token = _register_and_login(client, "review-owner@example.com", "Review Owner")
    other_token = _register_and_login(client, "review-other@example.com", "Review Other")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    run_id = _seed_review_run(_user_id(client, owner_token), _user_id(client, other_token))

    owner_queue = client.get("/api/v1/evidence-gate/reviews", headers=owner_headers)
    assert owner_queue.status_code == 200, owner_queue.text
    assert owner_queue.json()["total"] == 1
    assert owner_queue.json()["items"][0]["id"] == run_id
    assert owner_queue.json()["items"][0]["review_status"] == "pending"
    assert client.get("/api/v1/evidence-gate/reviews", headers=other_headers).json()["total"] == 0

    forbidden_detail = client.get(f"/api/v1/evidence-gate/reviews/{run_id}", headers=other_headers)
    assert forbidden_detail.status_code == 404
    forbidden_decision = client.post(
        f"/api/v1/evidence-gate/reviews/{run_id}/decisions",
        headers=other_headers,
        json={"decision": "accepted", "expected_version": 0},
    )
    assert forbidden_decision.status_code == 404

    detail = client.get(f"/api/v1/evidence-gate/reviews/{run_id}", headers=owner_headers)
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["review_version"] == 0
    assert payload["claims"][0]["sources"] == [
        {
            "source_number": 1,
            "document_id": "review-owner-document",
            "document_name": "owner.pdf",
            "chunk_id": "owner-chunk",
            "chunk_index": 3,
            "page_number": 2,
            "bbox": {"x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0, "page_number": 2},
            "section_title": "Owner section",
            "chunk_type": "text",
            "content": "Owner evidence snapshot.",
            "similarity_score": 0.97,
            "citation_label": "owner citation",
        }
    ]
    assert payload["decision_history"] == []

    accepted = client.post(
        f"/api/v1/evidence-gate/reviews/{run_id}/decisions",
        headers=owner_headers,
        json={"decision": "accepted", "expected_version": 0, "note": "Evidence confirmed."},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["review_status"] == "accepted"
    assert accepted.json()["review_version"] == 1
    assert accepted.json()["decision_history"][0]["expected_version"] == 0
    assert accepted.json()["decision_history"][0]["result_version"] == 1
    assert accepted.json()["decision_history"][0]["reviewer_id"] == _user_id(client, owner_token)

    stale = client.post(
        f"/api/v1/evidence-gate/reviews/{run_id}/decisions",
        headers=owner_headers,
        json={"decision": "rejected", "expected_version": 0},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == "Review decision is stale; refresh and retry."

    rejected = client.post(
        f"/api/v1/evidence-gate/reviews/{run_id}/decisions",
        headers=owner_headers,
        json={"decision": "rejected", "expected_version": 1},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["review_status"] == "rejected"
    assert rejected.json()["review_version"] == 2
    assert [event["decision"] for event in rejected.json()["decision_history"]] == [
        "accepted",
        "rejected",
    ]
    assert [event["result_version"] for event in rejected.json()["decision_history"]] == [1, 2]
