import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.data_agent import DataAgent


@pytest.mark.asyncio
@patch("backend.agents.data_agent.DocumentProcessor")
async def test_ingest_document_parses_already_stored_local_copy(mock_document_processor_cls):
    """DataAgent only parses a local file; it must not perform any object
    storage upload itself. The caller (the Celery worker) is responsible for
    uploading to S3/MinIO and downloading its own local working copy before
    invoking this workflow, so a file is never written to S3 more than once.
    """
    processor = MagicMock()
    processor.parse_document = AsyncMock(return_value={"text": "parsed content", "metadata": {"type": "pdf"}})
    mock_document_processor_cls.return_value = processor

    agent = DataAgent()
    assert not hasattr(agent, "file_storage")

    result = await agent.process(
        {
            "task_type": "ingest",
            "file_path": "/tmp/worker-local/sample.pdf",
            "filename": "sample.pdf",
            "s3_key": "documents/sample.pdf",
        }
    )

    processor.parse_document.assert_awaited_once_with("/tmp/worker-local/sample.pdf")
    assert result["success"] is True
    assert result["stored_path"] == "documents/sample.pdf"
    assert result["content"]["text"] == "parsed content"
