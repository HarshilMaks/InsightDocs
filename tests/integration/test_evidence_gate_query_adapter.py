from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.core.limiter import limiter
from backend.middleware.guardrails import check_input_guardrail
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
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


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
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "SecurePass123!"},
    )
    assert registered.status_code == 201, registered.text
    logged_in = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "SecurePass123!"},
    )
    assert logged_in.status_code == 200, logged_in.text
    return logged_in.json()["token"]["access_token"]


def _user_id(client: TestClient, token: str) -> str:
    response = client.get("/api/v1/users/me/byok-status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    return response.json()["user_id"]


def _seed_document(user_id: str, document_id: str) -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            Document(
                id=document_id,
                filename="evidence.pdf",
                file_type=".pdf",
                file_size=1024,
                s3_bucket="test",
                s3_key=f"{document_id}.pdf",
                status=TaskStatus.COMPLETED,
                user_id=user_id,
            )
        )
        db.commit()
    finally:
        db.close()


def _result(document_id: str, claim_verifications):
    return {
        "success": True,
        "answer": "PostgreSQL stores document metadata.",
        "sources": [
            {
                "content": "PostgreSQL stores document metadata.",
                "score": 0.98,
                "metadata": {
                    "document_id": document_id,
                    "citation": {
                        "source_number": 1,
                        "document_id": document_id,
                        "document_name": "evidence.pdf",
                        "chunk_id": "chunk-evidence-1",
                        "chunk_index": 1,
                        "page_number": 2,
                        "bbox": {"x1": 72.0, "y1": 144.0, "x2": 336.0, "y2": 168.0},
                        "citation_label": "evidence.pdf · Page 2 · Chunk 1",
                    },
                },
            }
        ],
        "claim_verifications": claim_verifications,
    }


def _stored_run(query_id: str) -> EvidenceGateRun:
    db = TestingSessionLocal()
    try:
        run = db.query(EvidenceGateRun).filter(EvidenceGateRun.query_id == query_id).one()
        db.expunge(run)
        return run
    finally:
        db.close()


def test_query_persists_a_supported_shadow_audit_and_preserves_legacy_response(client):
    token = _register_and_login(client, "shadow-pass@example.com", "Shadow Pass")
    user_id = _user_id(client, token)
    _seed_document(user_id, "doc-shadow-pass")
    claims = [
        {
            "claim": "PostgreSQL stores document metadata.",
            "status": "supported",
            "supporting_sources": [1],
            "reason": None,
        }
    ]
    mock_orchestrator = AsyncMock()
    mock_orchestrator.process_query.return_value = _result("doc-shadow-pass", claims)

    with patch("backend.api.query._get_user_orchestrator", return_value=mock_orchestrator), patch(
        "backend.api.query.check_output",
        return_value=("PostgreSQL stores document metadata.", False),
    ):
        response = client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Which database stores document metadata?"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"] == "PostgreSQL stores document metadata."
    assert payload["claim_verifications"][0]["status"] == "supported"
    assert payload["evidence_gate"] == {
        "id": payload["evidence_gate"]["id"],
        "policy_version": "evidence-gate/v1",
        "mode": "shadow",
        "status": "passed",
        "action": "allow",
        "claim_count": 1,
        "supported_count": 1,
        "unsupported_count": 0,
        "unverified_count": 0,
        "verified_at": payload["evidence_gate"]["verified_at"],
    }

    run = _stored_run(payload["query_id"])
    assert run.user_id == user_id
    assert run.status == "passed"
    assert run.candidate_answer_sha256 == run.delivered_answer_sha256
    assert run.source_snapshot_sha256


def test_guard_substitution_is_audited_as_abstained_and_hides_stale_legacy_claims(client):
    token = _register_and_login(client, "shadow-abstain@example.com", "Shadow Abstain")
    user_id = _user_id(client, token)
    _seed_document(user_id, "doc-shadow-abstain")
    claims = [
        {
            "claim": "PostgreSQL stores document metadata.",
            "status": "supported",
            "supporting_sources": [1],
            "reason": None,
        }
    ]
    mock_orchestrator = AsyncMock()
    mock_orchestrator.process_query.return_value = _result("doc-shadow-abstain", claims)
    abstention = "I cannot provide a response from the supplied evidence."

    with patch("backend.api.query._get_user_orchestrator", return_value=mock_orchestrator), patch(
        "backend.api.query.check_output", return_value=(abstention, True)
    ):
        response = client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Which database stores document metadata?"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"] == abstention
    assert payload["claim_verifications"] is None
    assert payload["evidence_gate"]["status"] == "abstained"
    assert payload["evidence_gate"]["action"] == "abstain"

    db = TestingSessionLocal()
    try:
        run = db.query(EvidenceGateRun).filter(EvidenceGateRun.query_id == payload["query_id"]).one()
        claim = db.query(EvidenceGateClaim).filter(EvidenceGateClaim.gate_run_id == run.id).one()
        stored_query = db.get(Query, payload["query_id"])
        assert run.candidate_answer_sha256 != run.delivered_answer_sha256
        assert claim.claim_text == "PostgreSQL stores document metadata."
        assert stored_query.response_text == abstention
    finally:
        db.close()


def test_missing_verification_persists_degraded_shadow_audit_without_changing_answer(client):
    token = _register_and_login(client, "shadow-degraded@example.com", "Shadow Degraded")
    user_id = _user_id(client, token)
    _seed_document(user_id, "doc-shadow-degraded")
    mock_orchestrator = AsyncMock()
    mock_orchestrator.process_query.return_value = _result("doc-shadow-degraded", None)

    with patch("backend.api.query._get_user_orchestrator", return_value=mock_orchestrator), patch(
        "backend.api.query.check_output",
        return_value=("PostgreSQL stores document metadata.", False),
    ):
        response = client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Which database stores document metadata?"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["claim_verifications"] is None
    assert payload["evidence_gate"]["status"] == "degraded"
    run = _stored_run(payload["query_id"])
    assert run.error_code == "VERIFICATION_UNAVAILABLE"
    assert run.claim_count == 0


def test_audit_persistence_failure_does_not_break_existing_query_response(client):
    token = _register_and_login(client, "shadow-failure@example.com", "Shadow Failure")
    user_id = _user_id(client, token)
    _seed_document(user_id, "doc-shadow-failure")
    mock_orchestrator = AsyncMock()
    mock_orchestrator.process_query.return_value = _result("doc-shadow-failure", None)

    with patch("backend.api.query._get_user_orchestrator", return_value=mock_orchestrator), patch(
        "backend.api.query.check_output",
        return_value=("PostgreSQL stores document metadata.", False),
    ), patch("backend.api.query.persist_shadow_audit", side_effect=RuntimeError("audit storage unavailable")):
        response = client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Which database stores document metadata?"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"] == "PostgreSQL stores document metadata."
    assert payload["evidence_gate"] is None

    db = TestingSessionLocal()
    try:
        assert db.get(Query, payload["query_id"]) is not None
        assert db.query(EvidenceGateRun).filter(EvidenceGateRun.query_id == payload["query_id"]).count() == 0
    finally:
        db.close()
