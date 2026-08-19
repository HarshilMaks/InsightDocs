"""Backend utility package.

Exports are resolved lazily so importing a lightweight utility (for example the
LLM client) does not load document parsers, vector clients, or ML libraries in
the API process.
"""


def __getattr__(name: str):
    if name == "DocumentProcessor":
        from .document_processor import DocumentProcessor
        return DocumentProcessor
    if name in {"EmbeddingEngine", "get_embedding_engine"}:
        from .embeddings import EmbeddingEngine, get_embedding_engine
        return {
            "EmbeddingEngine": EmbeddingEngine,
            "get_embedding_engine": get_embedding_engine,
        }[name]
    if name == "LLMClient":
        from .llm_client import LLMClient
        return LLMClient
    raise AttributeError(f"module 'backend.utils' has no attribute {name!r}")


__all__ = [
    "DocumentProcessor",
    "EmbeddingEngine",
    "get_embedding_engine",
    "LLMClient",
]
