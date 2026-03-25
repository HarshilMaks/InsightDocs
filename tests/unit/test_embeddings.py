import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import numpy as np

from backend.config import settings
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


@patch("backend.utils.embeddings.SentenceTransformer")
def test_embedding_engine_uses_legacy_model_for_384_dim_collection(mock_sentence_transformer):
    mock_sentence_transformer.return_value = MagicMock()

    def fake_init_collection(self):
        self.collection = SimpleNamespace(
            schema=SimpleNamespace(
                fields=[SimpleNamespace(name="dense_vector", dim=384)]
            )
        )

    with patch.object(EmbeddingEngine, "_connect_milvus", lambda self: None), patch.object(
        EmbeddingEngine, "_init_collection", fake_init_collection
    ):
        engine = EmbeddingEngine()

    mock_sentence_transformer.assert_called_with(settings.legacy_embedding_model)
    assert engine.dimension == 384


@pytest.mark.asyncio
@patch("backend.utils.embeddings.SentenceTransformer")
@patch.object(EmbeddingEngine, "_connect_milvus", lambda self: None)
@patch.object(EmbeddingEngine, "_init_collection", lambda self: None)
async def test_embedding_engine_generates_hashed_sparse_vectors_without_dependency(mock_sentence_transformer):
    mock_sentence_transformer.return_value = MagicMock()
    mock_sentence_transformer.return_value.encode.return_value = np.array([[0.1, 0.2]])

    missing_sparse_module = types.ModuleType("milvus_model.hybrid")

    with patch.dict(sys.modules, {"milvus_model.hybrid": missing_sparse_module}):
        engine = EmbeddingEngine()

    embeddings = await engine.embed_texts(["hello hello world"])

    assert len(embeddings["dense"]) == 1
    assert len(embeddings["sparse"]) == 1
    assert isinstance(embeddings["sparse"][0], dict)
    assert embeddings["sparse"][0]
    assert all(isinstance(k, int) for k in embeddings["sparse"][0].keys())
    assert all(isinstance(v, float) for v in embeddings["sparse"][0].values())


@pytest.mark.asyncio
@patch("backend.utils.embeddings.SentenceTransformer")
@patch.object(EmbeddingEngine, "_connect_milvus", lambda self: None)
@patch.object(EmbeddingEngine, "_init_collection", lambda self: None)
@patch("pymilvus.AnnSearchRequest")
@patch("pymilvus.WeightedRanker")
async def test_embedding_engine_search_uses_hybrid_search_with_sparse_fallback(
    mock_weighted_ranker,
    mock_ann_search_request,
    mock_sentence_transformer,
):
    mock_sentence_transformer.return_value = MagicMock()

    missing_sparse_module = types.ModuleType("milvus_model.hybrid")

    with patch.dict(sys.modules, {"milvus_model.hybrid": missing_sparse_module}):
        engine = EmbeddingEngine()

    engine.collection = MagicMock()
    engine.collection.hybrid_search.return_value = [
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
    engine.embed_texts = AsyncMock(return_value={"dense": [[0.1, 0.2]], "sparse": [{123: 0.5}]})
    mock_ann_search_request.side_effect = ["dense_req", "sparse_req"]
    mock_weighted_ranker.return_value = "ranker"

    results = await engine.search("test query", top_k=5, user_id="user-1")

    assert mock_ann_search_request.call_count == 2
    assert mock_ann_search_request.call_args_list[0].kwargs["expr"] == 'user_id == "user-1"'
    assert mock_ann_search_request.call_args_list[1].kwargs["expr"] == 'user_id == "user-1"'

    engine.collection.hybrid_search.assert_called_once_with(
        reqs=["dense_req", "sparse_req"],
        rerank="ranker",
        limit=5,
        output_fields=["text", "document_id", "user_id"],
    )
    engine.collection.search.assert_not_called()
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


@pytest.mark.asyncio
@patch("backend.utils.embeddings.SentenceTransformer")
@patch.object(EmbeddingEngine, "_connect_milvus", lambda self: None)
@patch.object(EmbeddingEngine, "_init_collection", lambda self: None)
async def test_store_embeddings_returns_empty_list_for_no_texts(mock_sentence_transformer):
    mock_sentence_transformer.return_value = MagicMock()

    missing_sparse_module = types.ModuleType("milvus_model.hybrid")

    with patch.dict(sys.modules, {"milvus_model.hybrid": missing_sparse_module}):
        engine = EmbeddingEngine()

    engine.collection = MagicMock()
    result = await engine.store_embeddings({"dense": [], "sparse": []}, [], {"document_id": "doc-1", "user_id": "user-1"})

    engine.collection.insert.assert_not_called()
    assert result == []
