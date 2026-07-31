"""Integration tests for claim verification wired into the query pipeline
(Roadmap Phase 3, Milestone 3).

Verifies that OrchestratorAgent.process_query calls verify_claims after
generation and includes the results in its return value, and that the
/query/ API endpoint surfaces them as structured claim_verifications.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.agents.orchestrator import OrchestratorAgent
from backend.middleware.guardrails import check_input_guardrail
from backend.models.database import Base, get_db
from backend.models import Document, TaskStatus


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


class TestOrchestratorClaimVerificationWiring:
    @pytest.mark.asyncio
    async def test_process_query_includes_claim_verifications_in_result(self):
        with patch("backend.agents.analysis_agent.get_embedding_engine", return_value=MagicMock()):
            orchestrator = OrchestratorAgent(api_key=None)

        db = TestingSessionLocal()
        try:
            fake_embedding_engine = MagicMock()
            fake_embedding_engine.search = AsyncMock(return_value=[])

            with patch(
                "backend.utils.embeddings.get_embedding_engine", return_value=fake_embedding_engine
            ), patch.object(
                orchestrator.analysis_agent.llm_client,
                "generate_rag_response",
                new=AsyncMock(return_value="Gemini 2.5 Flash is the default model."),
            ), patch.object(
                orchestrator.planning_agent,
                "process",
                new=AsyncMock(return_value={"success": True, "suggestions": []}),
            ), patch(
                "backend.middleware.guardrails.verify_claims",
                return_value=[
                    {
                        "claim": "Gemini 2.5 Flash is the default model.",
                        "status": "supported",
                        "supporting_sources": [1],
                        "reason": None,
                    }
                ],
            ) as mock_verify:
                result = await orchestrator.process_query(
                    "what model do you use?",
                    user_id="user-1",
                    db=db,
                )

            assert result["success"] is True
            mock_verify.assert_called_once()
            assert result["claim_verifications"] == [
                {
                    "claim": "Gemini 2.5 Flash is the default model.",
                    "status": "supported",
                    "supporting_sources": [1],
                    "reason": None,
                }
            ]
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_process_query_succeeds_even_if_verification_raises(self):
        """Claim verification failing must not fail the whole query — it
        is a non-fatal enhancement, not a required step."""
        with patch("backend.agents.analysis_agent.get_embedding_engine", return_value=MagicMock()):
            orchestrator = OrchestratorAgent(api_key=None)

        db = TestingSessionLocal()
        try:
            fake_embedding_engine = MagicMock()
            fake_embedding_engine.search = AsyncMock(return_value=[])

            with patch(
                "backend.utils.embeddings.get_embedding_engine", return_value=fake_embedding_engine
            ), patch.object(
                orchestrator.analysis_agent.llm_client,
                "generate_rag_response",
                new=AsyncMock(return_value="An answer."),
            ), patch.object(
                orchestrator.planning_agent,
                "process",
                new=AsyncMock(return_value={"success": True, "suggestions": []}),
            ), patch(
                "backend.middleware.guardrails.verify_claims",
                side_effect=RuntimeError("verification service unreachable"),
            ):
                result = await orchestrator.process_query(
                    "what model do you use?",
                    user_id="user-1",
                    db=db,
                )

            assert result["success"] is True
            assert result["answer"] == "An answer."
            assert result["claim_verifications"] is None
        finally:
            db.close()


class TestQueryEndpointClaimVerificationContract:
    def test_query_response_includes_claim_verifications_field(self, client):
        token = _register_and_login(client, "verifieduser@example.com", "Verified User")

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": True,
            "answer": "The system uses PostgreSQL.",
            "sources": [],
            "claim_verifications": [
                {
                    "claim": "The system uses PostgreSQL.",
                    "status": "supported",
                    "supporting_sources": [1],
                    "reason": None,
                }
            ],
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "what database is used?"},
            )

        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["claim_verifications"] is not None
        assert payload["claim_verifications"][0]["claim"] == "The system uses PostgreSQL."
        assert payload["claim_verifications"][0]["status"] == "supported"
        assert payload["claim_verifications"][0]["supporting_sources"] == [1]

    def test_query_response_claim_verifications_is_null_when_unavailable(self, client):
        token = _register_and_login(client, "unverifieduser@example.com", "Unverified User")

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": True,
            "answer": "An answer with no verification available.",
            "sources": [],
            "claim_verifications": None,
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "anything"},
            )

        assert r.status_code == 200, r.text
        assert r.json()["claim_verifications"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
