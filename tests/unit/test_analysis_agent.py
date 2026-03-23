import pytest
from unittest.mock import MagicMock, patch

from backend.agents.analysis_agent import AnalysisAgent


@pytest.mark.asyncio
@patch("backend.agents.analysis_agent.get_embedding_engine")
@patch("backend.agents.analysis_agent.LLMClient")
async def test_analysis_agent_rejects_empty_chunks(mock_llm_client_cls, mock_get_embedding_engine):
    mock_get_embedding_engine.return_value = MagicMock()
    mock_llm_client_cls.return_value = MagicMock()

    agent = AnalysisAgent(api_key="test-key")
    result = await agent.process({"task_type": "embed", "chunks": [], "metadata": {}})

    assert result["success"] is False
    assert "No text chunks available" in result["error"]
