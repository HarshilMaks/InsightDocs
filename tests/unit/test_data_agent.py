import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.data_agent import DataAgent


@pytest.mark.asyncio
@patch("backend.agents.data_agent.DocumentProcessor")
@patch("backend.agents.data_agent.FileStorage")
async def test_ingest_document_parses_local_file_before_upload(mock_file_storage_cls, mock_document_processor_cls):
    processor = MagicMock()
    processor.parse_document = AsyncMock(return_value={"text": "parsed content", "metadata": {"type": "pdf"}})

    storage = MagicMock()
    storage.store_file = AsyncMock(return_value="documents/sample.pdf")
    storage.bucket_name = "insightdocs"

    mock_document_processor_cls.return_value = processor
    mock_file_storage_cls.return_value = storage

    agent = DataAgent()
    result = await agent.process(
        {
            "task_type": "ingest",
            "file_path": "/tmp/uploaded/sample.pdf",
            "filename": "sample.pdf",
        }
    )

    storage.store_file.assert_awaited_once_with("/tmp/uploaded/sample.pdf", "sample.pdf")
    processor.parse_document.assert_awaited_once_with("/tmp/uploaded/sample.pdf")
    assert result["success"] is True
    assert result["stored_path"] == "documents/sample.pdf"
    assert result["content"]["text"] == "parsed content"
