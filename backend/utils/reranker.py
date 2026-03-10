"""Cross-Encoder Reranker for RAG pipeline.

After the hybrid retrieval step returns top-K chunks, the Reranker
scores each (query, chunk) pair using a cross-encoder model and
re-orders them by semantic relevance before passing to the LLM.

Cross-encoders are much more accurate than bi-encoders (embedding
similarity) because they see both texts at the same time.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - Fast and accurate (6 layers)
  - Trained on MS MARCO passage ranking
  - Returns a relevance score (float) per pair
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Reranker:
    """Reranks retrieved chunks using a cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model_name
        self._model = None  # Lazy-load to avoid import cost at startup
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self._model_name)
            self._available = True
            logger.info(f"Reranker loaded: {self._model_name}")
        except Exception as e:
            logger.warning(f"Reranker unavailable (falling back to original order): {e}")

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rerank search results by relevance to the query.

        Args:
            query:   The user's query string.
            results: List of search result dicts, each containing 'text'.
            top_n:   Number of top results to return after reranking.

        Returns:
            Reranked and truncated list of results.
        """
        if not results:
            return results

        # Fallback: return as-is when model unavailable
        if not self._available or self._model is None:
            logger.debug("Reranker not available, returning original order")
            return results[:top_n]

        try:
            pairs = [(query, r["text"]) for r in results]
            scores = self._model.predict(pairs)

            # Attach rerank score and sort descending
            for result, score in zip(results, scores):
                result["rerank_score"] = float(score)

            reranked = sorted(results, key=lambda r: r["rerank_score"], reverse=True)
            logger.info(
                f"Reranked {len(results)} results → returning top {top_n}"
            )
            return reranked[:top_n]

        except Exception as e:
            logger.error(f"Reranking failed, returning original order: {e}")
            return results[:top_n]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_reranker_instance: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Return the singleton Reranker instance (lazy-initialised)."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker()
    return _reranker_instance
