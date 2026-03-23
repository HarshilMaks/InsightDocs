import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.utils.embeddings import EmbeddingEngine


@patch("backend.utils.embeddings.SentenceTransformer")
@patch.object(EmbeddingEngine, "_connect_milvus", lambda self: None)
@patch.object(EmbeddingEngine, "_init_collection", lambda self: None)
def test_embedding_engine_disables_sparse_model_when_dependency_missing(mock_sentence_transformer):
    mock_sentence_transformer.return_value = MagicMock()

    missing_sparse_module = types.ModuleType("milvus_model.hybrid")

    with patch.dict(sys.modules, {"milvus_model.hybrid": missing_sparse_module}):
        engine = EmbeddingEngine()

    assert engine.has_sparse is False
    assert engine.sparse_model is None


@pytest.mark.asyncio
@patch("backend.utils.embeddings.SentenceTransformer")
@patch.object(EmbeddingEngine, "_connect_milvus", lambda self: None)
@patch.object(EmbeddingEngine, "_init_collection", lambda self: None)
async def test_embedding_engine_search_falls_back_to_dense_only(mock_sentence_transformer):
    mock_sentence_transformer.return_value = MagicMock()

    missing_sparse_module = types.ModuleType("milvus_model.hybrid")

    with patch.dict(sys.modules, {"milvus_model.hybrid": missing_sparse_module}):
        engine = EmbeddingEngine()

    engine.collection = MagicMock()
    engine.collection.search.return_value = [
        [
            SimpleNamespace(
                id="chunk-1",
                score=0.91,
                entity={
                    "text": "relevant chunk",
                    "document_id": "doc-1",
                    "user_id": "user-1",
                },
            )
        ]
    ]
    engine.embed_texts = AsyncMock(return_value={"dense": [[0.1, 0.2]], "sparse": [{}]})

    results = await engine.search("test query", top_k=5, user_id="user-1")

    engine.collection.search.assert_called_once()
    engine.collection.hybrid_search.assert_not_called()
    assert results == [
        {
            "id": "chunk-1",
            "text": "relevant chunk",
            "score": 0.91,
            "metadata": {
                "document_id": "doc-1",
                "user_id": "user-1",
            },
        }
    ]
