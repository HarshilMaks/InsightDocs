"""Backend hardening tests for worker ownership, task failures, and rate-limit identity isolation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.limiter import _rate_limit_key
from backend.workers import tasks


class _DummyReq:
    def __init__(self, auth: str | None = None, host: str = "127.0.0.1"):
        self.headers = {}
        if auth:
            self.headers["authorization"] = auth
        self.client = type("Client", (), {"host": host})()


def _fake_db_with_no_doc():
    db = MagicMock()
    doc_query = MagicMock()
    db.query.return_value = doc_query
    doc_filter = MagicMock()
    doc_query.filter.return_value = doc_filter
    doc_filter.first.return_value = None
    return db


def _fake_db_with_doc(doc, chunks=None):
    db = MagicMock()
    chunks = chunks or []

    class _Query:
        def __init__(self, first_obj=None, all_rows=None):
            self._first_obj = first_obj
            self._all_rows = all_rows or []

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self._first_obj

        def all(self):
            return self._all_rows

    def _query_side_effect(model):
        model_name = getattr(model, "__name__", "")
        if model_name == "Document":
            return _Query(first_obj=doc, all_rows=[])
        if model_name == "DocumentChunk":
            return _Query(first_obj=None, all_rows=chunks)
        return _Query(first_obj=None, all_rows=[])

    db.query.side_effect = _query_side_effect
    db.commit = MagicMock()
    return db


class TestRateLimitIdentity:
    def test_rate_limit_key_uses_user_id_when_token_valid(self):
        req = _DummyReq(auth="Bearer token123", host="10.0.0.1")
        with patch("backend.core.limiter.decode_token") as mock_decode:
            mock_decode.return_value = type("TD", (), {"user_id": "u-1"})()
            key = _rate_limit_key(req)
        assert key == "user:u-1"

    def test_rate_limit_key_falls_back_to_ip(self):
        req = _DummyReq(host="10.0.0.9")
        key = _rate_limit_key(req)
        assert key.startswith("ip:")


class TestWorkerOwnershipEnforcement:
    def test_process_document_task_requires_user_id(self):
        fake_db = _fake_db_with_no_doc()

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch("backend.workers.tasks._update_task") as mock_update_task:
            result = tasks.process_document_task.run("doc-1", "/tmp/x.pdf", "x.pdf", None)

        assert result["success"] is False
        assert "user_id is required" in result["error"]
        mock_update_task.assert_called()

    def test_generate_embeddings_task_requires_user_id(self):
        fake_db = _fake_db_with_no_doc()

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch("backend.workers.tasks._update_task") as mock_update_task:
            result = tasks.generate_embeddings_task.run("doc-1", ["chunk"], None)

        assert result["success"] is False
        assert "user_id is required" in result["error"]
        mock_update_task.assert_called()

    def test_generate_podcast_task_requires_user_id(self):
        fake_db = _fake_db_with_no_doc()

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch("backend.workers.tasks._update_task") as mock_update_task:
            result = tasks.generate_podcast_task.run("doc-1", None)

        assert result["success"] is False
        assert "user_id is required" in result["error"]
        mock_update_task.assert_called()

    def test_process_document_task_rejects_unowned_document(self):
        fake_db = _fake_db_with_no_doc()

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch("backend.workers.tasks._update_task") as mock_update_task:
            result = tasks.process_document_task.run("doc-x", "/tmp/x.pdf", "x.pdf", "user-1")

        assert result["success"] is False
        assert "not found for user" in result["error"]
        mock_update_task.assert_called()


class TestPodcastFailureHandling:
    def test_generate_podcast_returns_failure_when_audio_not_generated(self):
        doc = type("Doc", (), {"filename": "d.pdf", "has_podcast": False, "podcast_s3_key": None, "podcast_duration": None})()
        chunk = type("Chunk", (), {"content": "hello world"})()
        fake_db = _fake_db_with_doc(doc, chunks=[chunk])

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch("backend.utils.llm_client.LLMClient.generate_podcast_script", new_callable=AsyncMock, return_value="script"), patch(
            "backend.utils.podcast_generator.PodcastGenerator.generate_podcast_from_text",
            return_value=(None, 0.0),
        ), patch("backend.workers.tasks._update_task") as mock_update_task, patch(
            "backend.storage.file_storage.FileStorage"
        ):
            result = tasks.generate_podcast_task.run("doc-1", "user-1")

        assert result["success"] is False
        assert "Audio generation failed" in result["error"]
        mock_update_task.assert_called()

    def test_generate_podcast_handles_s3_failure(self):
        doc = type("Doc", (), {"filename": "d.pdf", "has_podcast": False, "podcast_s3_key": None, "podcast_duration": None})()
        chunk = type("Chunk", (), {"content": "hello world"})()
        fake_db = _fake_db_with_doc(doc, chunks=[chunk])

        with patch("backend.workers.tasks._create_db_session", return_value=(fake_db, object())), patch(
            "backend.workers.tasks._close_db_session"
        ), patch(
            "backend.utils.llm_client.LLMClient.generate_podcast_script",
            new_callable=AsyncMock,
            return_value="script",
        ), patch(
            "backend.utils.podcast_generator.PodcastGenerator.generate_podcast_from_text",
            return_value=(b"audio-bytes", 5.0),
        ), patch("backend.workers.tasks._update_task") as mock_update_task, patch(
            "backend.storage.file_storage.FileStorage"
        ) as mock_storage_cls:
            mock_storage = MagicMock()
            mock_storage.store_file = AsyncMock(side_effect=RuntimeError("S3 unavailable"))
            mock_storage_cls.return_value = mock_storage
            result = tasks.generate_podcast_task.run("doc-1", "user-1")

        assert result["success"] is False
        assert "S3 unavailable" in result["error"]
        mock_update_task.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
