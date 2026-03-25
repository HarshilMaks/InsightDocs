"""Integration tests for citation-backed RAG chat."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock, patch

from backend.api.main import app
from backend.agents.orchestrator import OrchestratorAgent
from backend.middleware.guardrails import check_input_guardrail
from backend.models.database import Base, get_db
from backend.models import Document, DocumentChunk, Query as QueryModel, TaskStatus
from backend.models.schemas import User


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


def _user_id_from_token(client: TestClient, token: str) -> str:
    r = client.get("/api/v1/users/me/byok-status", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


class TestCitationResponseContract:
    def test_query_endpoint_returns_structured_citations(self, client):
        token = _register_and_login(client, "citations@example.com", "Citation User")
        user_id = _user_id_from_token(client, token)

        db = TestingSessionLocal()
        try:
            db.add(
                Document(
                    id="doc-cite-1",
                    filename="report.pdf",
                    file_type=".pdf",
                    file_size=1234,
                    s3_bucket="bucket",
                    s3_key="report.pdf",
                    status=TaskStatus.COMPLETED,
                    user_id=user_id,
                )
            )
            db.commit()
        finally:
            db.close()

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": True,
            "answer": "The answer is supported by [1].",
            "sources": [
                {
                    "content": "The report states this on page 12.",
                    "score": 0.98,
                    "metadata": {
                        "document_id": "doc-cite-1",
                        "citation": {
                            "source_number": 1,
                            "document_id": "doc-cite-1",
                            "document_name": "report.pdf",
                            "chunk_id": "chunk-1",
                            "chunk_index": 5,
                            "page_number": 12,
                            "bbox": {"x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0},
                            "citation_label": "report.pdf · Page 12 · Chunk 5",
                        },
                    },
                }
            ],
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "Where is this mentioned?"},
            )

        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["answer"].endswith("[1].")
        assert payload["conversation_id"]
        assert payload["turn_index"] == 1
        assert payload["sources"], payload

        source = payload["sources"][0]
        assert source["source_number"] == 1
        assert source["document_id"] == "doc-cite-1"
        assert source["document_name"] == "report.pdf"
        assert source["chunk_id"] == "chunk-1"
        assert source["chunk_index"] == 5
        assert source["page_number"] == 12
        assert source["citation_label"] == "report.pdf · Page 12 · Chunk 5"
        assert source["bbox"]["x1"] == 1.0


class TestConversationThreading:
    def test_query_endpoint_threads_follow_up_questions(self, client):
        token = _register_and_login(client, "threaded@example.com", "Threaded User")
        user_id = _user_id_from_token(client, token)

        seed_db = TestingSessionLocal()
        try:
            seed_db.add(
                Document(
                    id="doc-thread-1",
                    filename="thread.pdf",
                    file_type=".pdf",
                    file_size=1234,
                    s3_bucket="bucket",
                    s3_key="thread.pdf",
                    status=TaskStatus.COMPLETED,
                    user_id=user_id,
                )
            )
            seed_db.add(
                QueryModel(
                    id="query-thread-1",
                    query_text="What is the document about?",
                    response_text="It is about AI-assisted document analysis.",
                    response_time=1.1,
                    user_id=user_id,
                    conversation_id="conv-thread-1",
                    turn_index=1,
                    sources=[],
                )
            )
            seed_db.commit()
        finally:
            seed_db.close()

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {
            "success": True,
            "answer": "The follow-up answer is supported by [1].",
            "sources": [
                {
                    "content": "The report states this on page 12.",
                    "score": 0.98,
                    "metadata": {
                        "document_id": "doc-thread-1",
                        "citation": {
                            "source_number": 1,
                            "document_id": "doc-thread-1",
                            "document_name": "thread.pdf",
                            "chunk_id": "chunk-thread-1",
                            "chunk_index": 5,
                            "page_number": 12,
                            "bbox": {"x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0},
                            "citation_label": "thread.pdf · Page 12 · Chunk 5",
                        },
                    },
                }
            ],
        }

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "Tell me more about it", "conversation_id": "conv-thread-1"},
            )

        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["conversation_id"] == "conv-thread-1"
        assert payload["turn_index"] == 2

        verify_db = TestingSessionLocal()
        try:
            rows = (
                verify_db.query(QueryModel)
                .filter(QueryModel.conversation_id == "conv-thread-1")
                .order_by(QueryModel.turn_index.asc())
                .all()
            )
            assert len(rows) == 2
            assert [row.turn_index for row in rows] == [1, 2]
            assert rows[1].query_text == "Tell me more about it"
        finally:
            verify_db.close()

        history = client.get(
            "/api/v1/query/history",
            params={"conversation_id": "conv-thread-1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert history.status_code == 200, history.text
        history_payload = history.json()
        assert history_payload["total"] == 2
        assert [item["turn_index"] for item in history_payload["queries"]] == [1, 2]
        assert history_payload["queries"][1]["conversation_id"] == "conv-thread-1"


class TestCitationPromptFormatting:
    @pytest.mark.asyncio
    async def test_llm_prompt_includes_source_labels_and_locations(self):
        with patch("backend.utils.llm_client.genai.GenerativeModel") as mock_model_cls:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = MagicMock(text="Answer with citations")
            mock_model_cls.return_value = mock_model

            from backend.utils.llm_client import LLMClient

            llm = LLMClient(api_key="AIzaSyC_test_key_for_citations_123")
            response = await llm.generate_rag_response(
                "What is the document about?",
                [
                    {
                        "text": "The report states this on page 12.",
                        "citation": {
                            "citation_label": "report.pdf · Page 12 · Chunk 5",
                            "document_name": "report.pdf",
                            "page_number": 12,
                            "chunk_index": 5,
                        },
                    }
                ],
                conversation_history=[
                    {
                        "query": "What is the document about?",
                        "response": "It is a report about AI documents.",
                    }
                ],
            )

        prompt = mock_model.generate_content.call_args.args[0]
        assert "cite every factual claim inline" in prompt.lower()
        assert "report.pdf · Page 12 · Chunk 5" in prompt
        assert "page 12" in prompt
        assert "chunk 5" in prompt
        assert "Conversation history:" in prompt
        assert "It is a report about AI documents." in prompt
        assert response == "Answer with citations"


class TestOrchestratorCitationEnrichment:
    @pytest.mark.asyncio
    async def test_orchestrator_passes_page_and_chunk_citations_to_llm(self):
        db = TestingSessionLocal()
        try:
            user = User(
                id="user-cite-1",
                email="user@example.com",
                name="User Cite",
                hashed_password="hashed",
            )
            document = Document(
                id="doc-cite-2",
                filename="guide.pdf",
                file_type=".pdf",
                file_size=2048,
                s3_bucket="bucket",
                s3_key="guide.pdf",
                status=TaskStatus.COMPLETED,
                user_id=user.id,
            )
            chunk = DocumentChunk(
                id="chunk-cite-1",
                document_id=document.id,
                chunk_index=4,
                content="Relevant passage from page 7.",
                milvus_id="milvus-1",
                page_number=7,
                bbox_x1=10.0,
                bbox_y1=20.0,
                bbox_x2=30.0,
                bbox_y2=40.0,
            )
            db.add(
                QueryModel(
                    id="query-history-1",
                    query_text="What does the guide explain?",
                    response_text="It explains the workflow for uploading documents.",
                    response_time=1.5,
                    user_id=user.id,
                    conversation_id="conv-cite-1",
                    turn_index=1,
                    sources=[],
                )
            )
            db.add_all([user, document, chunk])
            db.commit()
        finally:
            db.close()

        mock_analysis = MagicMock()
        mock_analysis.llm_client.generate_rag_response = AsyncMock(return_value="Answer with citations")
        mock_analysis.process = AsyncMock()
        mock_planning = MagicMock()
        mock_planning.process = AsyncMock(return_value={"success": True})

        request_db = TestingSessionLocal()
        try:
            with patch("backend.agents.orchestrator.AnalysisAgent", return_value=mock_analysis), patch(
                "backend.agents.orchestrator.PlanningAgent", return_value=mock_planning
            ), patch("backend.utils.embeddings.get_embedding_engine") as mock_engine_factory, patch(
                "backend.utils.reranker.get_reranker"
            ) as mock_reranker_factory:
                mock_engine = MagicMock()
                mock_engine.search = AsyncMock(
                    return_value=[
                        {
                            "id": "milvus-1",
                            "text": "Relevant passage from page 7.",
                            "score": 0.97,
                            "metadata": {
                                "document_id": document.id,
                                "user_id": user.id,
                            },
                        }
                    ]
                )
                mock_engine_factory.return_value = mock_engine

                mock_reranker = MagicMock()
                mock_reranker.rerank.return_value = [
                    {
                        "id": "milvus-1",
                        "text": "Relevant passage from page 7.",
                        "score": 0.97,
                        "metadata": {
                            "document_id": document.id,
                            "user_id": user.id,
                        },
                    }
                ]
                mock_reranker_factory.return_value = mock_reranker

                orchestrator = OrchestratorAgent(api_key="AIzaSyC_test_key_for_citations_123")
                result = await orchestrator.process_query(
                    "Where is this mentioned?",
                    user_id=user.id,
                    conversation_id="conv-cite-1",
                    db=request_db,
                )
        finally:
            request_db.close()

        assert result["success"] is True
        assert result["sources"]
        assert result["sources"][0]["metadata"]["citation"]["page_number"] == 7
        assert result["sources"][0]["metadata"]["citation"]["chunk_index"] == 5
        assert result["sources"][0]["metadata"]["citation"]["citation_label"] == "guide.pdf · Page 7 · Chunk 5"
        assert result["conversation_history"][0]["query"] == "What does the guide explain?"

        context_chunks = mock_analysis.llm_client.generate_rag_response.await_args.args[1]
        assert context_chunks[0]["citation"]["page_number"] == 7
        assert context_chunks[0]["citation"]["chunk_index"] == 5
        assert context_chunks[0]["citation"]["document_name"] == "guide.pdf"
        assert mock_analysis.llm_client.generate_rag_response.await_args.kwargs["conversation_history"][0]["response"] == "It explains the workflow for uploading documents."
