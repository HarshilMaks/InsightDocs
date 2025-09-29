"""
RAG Service
Handles retrieval-augmented generation: embed → retrieve → generate
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from pymilvus import Collection
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.milvus import get_collection
from models.schemas import QueryRequest
from utils.logger import get_logger, log_performance
from services.llm_service import LLMService


settings = get_settings()


@dataclass
class RetrievedContext:
    content: str
    document_id: str
    document_name: str
    similarity_score: float
    metadata: Dict[str, Any]


@dataclass
class RAGResponse:
    answer: str
    sources: List[RetrievedContext]
    query: str
    response_time: float
    tokens_used: int
    confidence_score: float


class RAGService:
    def __init__(self):
        self.logger = get_logger("rag")
        self.llm = LLMService()

    async def query_documents(
        self, query: QueryRequest, session: Optional[AsyncSession] = None
    ) -> RAGResponse:
        """Main RAG pipeline: embed → retrieve → generate"""
        start = time.time()

        try:
            # 1. Embed user query
            query_embedding = await self.llm.embed_text(query.query)

            # 2. Retrieve contexts from Milvus
            contexts = await self._retrieve_contexts(query_embedding, query.max_results or 5)
            if not contexts:
                return RAGResponse(
                    answer="No relevant documents found.",
                    sources=[],
                    query=query.query,
                    response_time=time.time() - start,
                    tokens_used=0,
                    confidence_score=0.0,
                )

            # 3. Generate answer based on retrieved contexts
            response = await self.llm.generate_response(
                prompt=self._build_prompt(query.query, contexts)
            )

            return RAGResponse(
                answer=response["answer"],
                sources=contexts,
                query=query.query,
                response_time=time.time() - start,
                tokens_used=response["usage"]["total_tokens"],
                confidence_score=0.8,  # TODO: compute confidence from similarity, etc.
            )

        except Exception as e:
            self.logger.error(f"RAG failed: {e}", exc_info=True)
            log_performance("rag_query", time.time() - start, success=False)
            raise

    async def _retrieve_contexts(self, embedding: List[float], top_k: int) -> List[RetrievedContext]:
        """Retrieve top-k relevant contexts from Milvus"""
        collection: Collection = await get_collection()

        # Perform vector similarity search
        results = collection.search(
            data=[embedding],
            anns_field="embedding",
            param={"metric_type": settings.milvus_metric},
            limit=top_k,
            output_fields=["content", "document_id", "document_name", "metadata"],
        )

        # Flatten Milvus results
        contexts: List[RetrievedContext] = []
        for hits in results:  # results is a list of lists
            for hit in hits:
                contexts.append(
                    RetrievedContext(
                        content=hit.entity.get("content", ""),
                        document_id=hit.entity.get("document_id", ""),
                        document_name=hit.entity.get("document_name", "Unknown"),
                        similarity_score=float(hit.score),
                        metadata=hit.entity.get("metadata", {}),
                    )
                )
        return contexts

    def _build_prompt(self, query: str, contexts: List[RetrievedContext]) -> str:
        """Assemble final prompt for the LLM"""
        context_text = "\n\n".join(
            [f"[{c.document_name}] {c.content[:500]}" for c in contexts]
        )
        return f"""
You are an AI assistant. Use ONLY the provided context to answer the question.

Context:
{context_text}

Question: {query}

Instructions:
- Be clear and concise
- Reference the relevant [document names]
- If the answer cannot be found in the context, say so.
"""