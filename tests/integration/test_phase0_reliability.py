"""Tests for Phase 0 reliability fixes:

- Upload handoff: the API uploads to S3/MinIO first and queues an object
  key (not a local temp path); the worker downloads its own local copy and
  cleans it up regardless of success or failure.
- Chunk-persistence failure is fatal to the ingestion workflow instead of
  being silently swallowed.
- Document-scoped querying: QueryRequest.document_id restricts retrieval to
  a single, ownership-verified document.
"""
import os
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
from backend.workers import tasks


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


class TestUploadHandoff:
    def test_upload_stores_to_object_storage_and_queues_object_key(self, client):
        """The upload endpoint must upload to S3/MinIO before queuing, and
        pass only the resulting object key (not a local filesystem path)
        to the Celery task, so a separately-deployed worker can retrieve it.
        """
        token = _register_and_login(client, "uploader@example.com", "Uploader")

        fake_storage = MagicMock()
        fake_storage.bucket_name = "insightdocs"
        fake_storage.store_bytes = AsyncMock(return_value="documents/unique-key-report.txt")

        with patch("backend.api.documents.FileStorage", return_value=fake_storage), patch(
            "backend.api.documents.process_document_task"
        ) as mock_task:
            mock_task.apply_async.return_value = MagicMock(id="task-123")

            r = client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("report.txt", b"hello world", "text/plain")},
            )

        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["success"] is True
        assert payload["task_id"] == "task-123"

        fake_storage.store_bytes.assert_awaited_once()
        awaited_args = fake_storage.store_bytes.await_args
        assert awaited_args.args[0] == b"hello world"
        assert awaited_args.args[1] == "report.txt"

        # The queued task must receive the object key, not a local path.
        queued_args = mock_task.apply_async.call_args.kwargs["args"]
        document_id, queued_key, filename, user_id = queued_args
        assert queued_key == "documents/unique-key-report.txt"
        assert not os.path.isabs(queued_key) or not os.path.exists(queued_key)
        assert filename == "report.txt"

        db = TestingSessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            assert doc is not None
            assert doc.s3_key == "documents/unique-key-report.txt"
            assert doc.s3_bucket == "insightdocs"
        finally:
            db.close()

    def test_worker_downloads_own_copy_and_cleans_up_temp_file(self):
        """The worker must download its own local copy of the object-store
        file and remove it when the task finishes, whether it succeeds or
        fails, so temp files never accumulate on the worker's disk."""
        doc = Document(
            id="doc-handoff-1",
            filename="report.txt",
            file_type=".txt",
            file_size=11,
            s3_bucket="insightdocs",
            s3_key="documents/report.txt",
            status=TaskStatus.PENDING,
            user_id="user-1",
        )

        fake_db = MagicMock()
        doc_query = MagicMock()
        fake_db.query.return_value = doc_query
        doc_query.filter.return_value = doc_query
        doc_query.first.return_value = doc

        written_paths = []
        real_download = None

        def fake_download_file(bucket, key, local_path):
            written_paths.append(local_path)
            with open(local_path, "wb") as f:
                f.write(b"downloaded bytes")

        fake_storage = MagicMock()
        fake_storage.bucket_name = "insightdocs"
        fake_storage.s3_client.download_file.side_effect = fake_download_file

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch("backend.workers.tasks._update_task"), patch(
            "backend.workers.tasks._update_document"
        ), patch(
            "backend.workers.tasks._get_owned_document", return_value=doc
        ), patch(
            "backend.workers.tasks._get_user_api_key", return_value=None
        ), patch(
            "backend.workers.tasks.FileStorage", return_value=fake_storage
        ), patch(
            "backend.workers.tasks.OrchestratorAgent"
        ) as mock_orchestrator_cls, patch(
            "backend.workers.tasks._run_async", return_value={"success": True, "document_id": "doc-handoff-1"}
        ):
            mock_orchestrator_cls.return_value = MagicMock()

            result = tasks.process_document_task.run(
                "doc-handoff-1", "documents/report.txt", "report.txt", "user-1"
            )

        assert result["success"] is True
        assert len(written_paths) == 1
        # The temp file must be removed after the task finishes.
        assert not os.path.exists(written_paths[0])

    def test_worker_cleans_up_temp_file_even_on_failure(self):
        """Cleanup must happen in a finally block: a downstream failure in
        the orchestrator must not leave the worker's temp file behind."""
        doc = Document(
            id="doc-handoff-2",
            filename="report.txt",
            file_type=".txt",
            file_size=11,
            s3_bucket="insightdocs",
            s3_key="documents/report.txt",
            status=TaskStatus.PENDING,
            user_id="user-1",
        )

        fake_db = MagicMock()
        doc_query = MagicMock()
        fake_db.query.return_value = doc_query
        doc_query.filter.return_value = doc_query
        doc_query.first.return_value = doc

        written_paths = []

        def fake_download_file(bucket, key, local_path):
            written_paths.append(local_path)
            with open(local_path, "wb") as f:
                f.write(b"downloaded bytes")

        fake_storage = MagicMock()
        fake_storage.bucket_name = "insightdocs"
        fake_storage.s3_client.download_file.side_effect = fake_download_file

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch("backend.workers.tasks._update_task"), patch(
            "backend.workers.tasks._update_document"
        ), patch(
            "backend.workers.tasks._get_owned_document", return_value=doc
        ), patch(
            "backend.workers.tasks._get_user_api_key", return_value=None
        ), patch(
            "backend.workers.tasks.FileStorage", return_value=fake_storage
        ), patch(
            "backend.workers.tasks.OrchestratorAgent"
        ) as mock_orchestrator_cls, patch(
            "backend.workers.tasks._run_async", side_effect=RuntimeError("boom")
        ):
            mock_orchestrator_cls.return_value = MagicMock()

            result = tasks.process_document_task.run(
                "doc-handoff-2", "documents/report.txt", "report.txt", "user-1"
            )

        assert result["success"] is False
        assert len(written_paths) == 1
        assert not os.path.exists(written_paths[0])


class TestFatalChunkPersistence:
    @pytest.mark.asyncio
    async def test_chunk_persistence_failure_fails_the_workflow(self):
        """A failure while persisting chunks to PostgreSQL must fail the
        whole ingestion workflow, not be logged and ignored, because a
        vector stored in Milvus with no matching DocumentChunk row can
        never be hydrated into a citation."""
        with patch("backend.agents.analysis_agent.get_embedding_engine", return_value=MagicMock()):
            orchestrator = OrchestratorAgent(api_key=None)
        with patch("backend.agents.analysis_agent.get_embedding_engine", return_value=MagicMock()):
            orchestrator = OrchestratorAgent(api_key=None)
            orchestrator.analysis_agent = MagicMock()
            orchestrator.analysis_agent.process = AsyncMock(side_effect=[
                {"success": True, "vector_ids": ["v1"], "embedding_count": 1},
                {"success": True, "summary": ""},
            ])
            orchestrator.planning_agent = MagicMock()
            orchestrator.planning_agent.process = AsyncMock(return_value={"success": True, "suggestions": []})

            fake_data_agent = MagicMock()
            fake_data_agent.process = AsyncMock(side_effect=[
                {
                    "success": True,
                    "stored_path": "documents/x.txt",
                    "content": {"text": "hello", "metadata": {}},
                },
                {"success": True, "chunks": [{"text": "hello"}], "chunk_count": 1},
            ])
            orchestrator.data_agent = fake_data_agent

            with patch.object(
                orchestrator, "_store_chunks_to_db", side_effect=RuntimeError("db unavailable")
            ), patch.object(orchestrator, "_update_document_ocr_info", new=AsyncMock()):
                result = await orchestrator._ingest_and_analyze_workflow({
                    "document_id": "doc-1",
                    "file_path": "/tmp/x.txt",
                    "s3_key": "documents/x.txt",
                    "filename": "x.txt",
                    "user_id": "user-1",
                    "task_id": "task-1",
                })

        assert result["success"] is False
        assert "chunk" in result["error"].lower()


class TestDocumentScopedQuery:
    def test_query_with_document_id_scopes_search_to_that_document(self, client):
        token = _register_and_login(client, "scoped@example.com", "Scoped User")
        user_id = _user_id_from_token(client, token)

        db = TestingSessionLocal()
        try:
            db.add(
                Document(
                    id="doc-scope-1",
                    filename="scoped.pdf",
                    file_type=".pdf",
                    file_size=100,
                    s3_bucket="bucket",
                    s3_key="scoped.pdf",
                    status=TaskStatus.COMPLETED,
                    user_id=user_id,
                )
            )
            db.commit()
        finally:
            db.close()

        mock_orch = AsyncMock()
        mock_orch.process_query.return_value = {"success": True, "answer": "scoped answer", "sources": []}

        with patch("backend.api.query._get_user_orchestrator", return_value=mock_orch):
            r = client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "what is this about?", "document_id": "doc-scope-1"},
            )

        assert r.status_code == 200, r.text
        mock_orch.process_query.assert_awaited_once()
        call_kwargs = mock_orch.process_query.await_args.kwargs
        assert call_kwargs["document_id"] == "doc-scope-1"

    @pytest.mark.asyncio
    async def test_process_query_ignores_document_scope_user_does_not_own(self):
        """If a user requests a document_id scope for a document they do
        not own, the scope must be ignored rather than leaking whether that
        document exists, and retrieval must fall back to the user's own
        documents."""
        with patch("backend.agents.analysis_agent.get_embedding_engine", return_value=MagicMock()):
            orchestrator = OrchestratorAgent(api_key=None)

        db = TestingSessionLocal()
        try:
            db.add(
                Document(
                    id="doc-not-mine",
                    filename="other.pdf",
                    file_type=".pdf",
                    file_size=10,
                    s3_bucket="bucket",
                    s3_key="other.pdf",
                    status=TaskStatus.COMPLETED,
                    user_id="someone-else",
                )
            )
            db.commit()

            fake_embedding_engine = MagicMock()
            fake_embedding_engine.search = AsyncMock(return_value=[])
            with patch(
                "backend.utils.embeddings.get_embedding_engine", return_value=fake_embedding_engine
            ), patch.object(
                orchestrator.analysis_agent.llm_client,
                "generate_rag_response",
                new=AsyncMock(return_value="an answer with no context"),
            ), patch.object(
                orchestrator.planning_agent,
                "process",
                new=AsyncMock(return_value={"success": True, "suggestions": []}),
            ):
                result = await orchestrator.process_query(
                    "hello",
                    user_id="requesting-user",
                    db=db,
                    document_id="doc-not-mine",
                )

            assert result["success"] is True
            fake_embedding_engine.search.assert_awaited_once()
            search_kwargs = fake_embedding_engine.search.await_args.kwargs
            assert search_kwargs["document_id"] is None
            assert search_kwargs["user_id"] == "requesting-user"
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
