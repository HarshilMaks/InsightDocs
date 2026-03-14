import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.utils.embeddings import EmbeddingEngine, get_embedding_engine
from backend.utils.reranker import Reranker, get_reranker
from backend.middleware.guardrails import InputGuardrailMiddleware, check_output

# Mock external services before importing dependent modules
@pytest.fixture(scope="module", autouse=True)
def mock_external_services():
    # Patch objects where they are defined or imported
    with patch("backend.utils.embeddings.connections"), \
         patch("backend.utils.embeddings.utility"), \
         patch("backend.utils.embeddings.Collection"), \
         patch("backend.utils.embeddings.SentenceTransformer"), \
         patch("milvus_model.hybrid.BGEM3EmbeddingFunction"), \
         patch("sentence_transformers.CrossEncoder"), \
         patch("google.generativeai.GenerativeModel"):
        yield

@pytest.fixture
def mock_embedding_engine():
    engine = MagicMock(spec=EmbeddingEngine)
    engine.embed_texts = AsyncMock(return_value={
        "dense": [[0.1, 0.2]],
        "sparse": [{"term1": 0.5}]
    })
    # Mock search result objects
    mock_hit1 = MagicMock()
    mock_hit1.id = "doc1"
    mock_hit1.score = 0.9
    mock_hit1.entity.get.side_effect = lambda k: "Content 1" if k == "text" else "doc1"

    mock_hit2 = MagicMock()
    mock_hit2.id = "doc2"
    mock_hit2.score = 0.8
    mock_hit2.entity.get.side_effect = lambda k: "Content 2" if k == "text" else "doc2"
    
    # Simulate hybrid search returning list of hits
    engine.search = AsyncMock(return_value=[
        {"id": "doc1", "text": "Content 1", "score": 0.9, "metadata": {"document_id": "doc1"}},
        {"id": "doc2", "text": "Content 2", "score": 0.8, "metadata": {"document_id": "doc2"}}
    ])
    return engine

@pytest.fixture
def mock_reranker():
    reranker = MagicMock(spec=Reranker)
    # Reranker should reorder: doc2 is more relevant than doc1
    reranker.rerank.return_value = [
        {"id": "doc2", "text": "Content 2", "score": 0.8, "metadata": {"document_id": "doc2"}, "rerank_score": 0.95},
        {"id": "doc1", "text": "Content 1", "score": 0.9, "metadata": {"document_id": "doc1"}, "rerank_score": 0.85}
    ]
    return reranker

@pytest.fixture
def client(mock_embedding_engine, mock_reranker):
    # Override dependencies
    app.dependency_overrides[get_embedding_engine] = lambda: mock_embedding_engine
    app.dependency_overrides[get_reranker] = lambda: mock_reranker
    return TestClient(app)

@pytest.mark.asyncio
async def test_hybrid_search_integration(mock_embedding_engine):
    """Test that hybrid search is called with correct parameters."""
    query = "test query"
    results = await mock_embedding_engine.search(query, top_k=10)
    
    mock_embedding_engine.search.assert_called_with(query, top_k=10)
    assert len(results) == 2
    assert results[0]["id"] == "doc1"

def test_reranker_logic():
    """Test reranker reordering logic using the real class with mocked model."""
    with patch("sentence_transformers.CrossEncoder") as MockEncoder:
        # Mock predict to return scores where second item is better
        mock_model = MockEncoder.return_value
        mock_model.predict.return_value = [0.1, 0.9] # Second item has higher score
        
        reranker = Reranker()
        results = [
            {"text": "low relevance", "id": "1"},
            {"text": "high relevance", "id": "2"}
        ]
        
        reranked = reranker.rerank("query", results)
        
        assert len(reranked) == 2
        assert reranked[0]["id"] == "2" # Should be first now
        assert reranked[0]["rerank_score"] == 0.9

def test_input_guardrail_middleware():
    """Test that input guardrail blocks unsafe content."""
    # We need to test the middleware logic directly or via client
    # Direct middleware test is cleaner for unit testing logic
    
    with patch("backend.middleware.guardrails._call_gemini_guard") as mock_guard:
        mock_guard.return_value = (False, "Prompt injection detected")
        
        client = TestClient(app)
        # Mock auth to bypass login for this test if possible, or use a public endpoint if guarded
        # But guardrail is on /query which is protected.
        # Alternatively, we can mock the dependency override for user.
        
        # Override auth
        async def mock_get_current_user():
            from backend.models.schemas import User
            return User(id="user1", email="test@example.com", is_active=True)
            
        app.dependency_overrides["backend.core.security.get_current_user"] = mock_get_current_user
        
        response = client.post("/api/v1/query/", json={"query": "ignore instructions", "top_k": 5})
        
        assert response.status_code == 400
        assert "Prompt injection detected" in response.json()["detail"]

def test_output_guardrail():
    """Test output guardrail flags hallucinations."""
    with patch("backend.middleware.guardrails._call_gemini_guard") as mock_guard:
        mock_guard.return_value = (False, "Unsupported claim")
        
        answer, flagged = check_output("Unverified answer", ["ctx1"])
        
        assert flagged is True
        assert "cannot provide a confident answer" in answer
