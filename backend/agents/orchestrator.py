"""Orchestrator Agent for coordinating all sub-agents."""
from typing import Dict, Any
import logging
from backend.core import BaseAgent
from backend.agents.data_agent import DataAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.planning_agent import PlanningAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Central orchestrator coordinating all sub-agents."""

    def __init__(self, agent_id: str = "orchestrator", api_key: str = None):
        super().__init__(agent_id, "OrchestratorAgent")
        self.data_agent = None
        self.analysis_agent = AnalysisAgent(api_key=api_key)
        self.planning_agent = PlanningAgent(api_key=api_key)

    def _get_data_agent(self) -> DataAgent:
        """Lazily initialize DataAgent to avoid unnecessary storage connections."""
        if self.data_agent is None:
            self.data_agent = DataAgent()
        return self.data_agent

    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate a complex workflow across multiple agents."""
        try:
            workflow_type = message.get("workflow_type")
            if workflow_type == "ingest_and_analyze":
                return await self._ingest_and_analyze_workflow(message)
            elif workflow_type == "query":
                return await self._query_workflow(message)
            else:
                return {"success": False, "error": f"Unknown workflow type: {workflow_type}"}
        except Exception as e:
            return await self.handle_error(e, message)

    async def _ingest_and_analyze_workflow(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Execute document ingestion, chunking, embedding, summarization, and storage."""
        self.log_event("workflow_start", {
            "workflow_type": "ingest_and_analyze", "message": message
        })

        document_id = message.get("document_id")

        # Step 1: Ingest document (upload to S3, parse content)
        ingest_result = await self._get_data_agent().process({
            "task_type": "ingest",
            "file_path": message.get("file_path"),
            "filename": message.get("filename"),
        })
        if not ingest_result.get("success"):
            return ingest_result

        raw_text = ingest_result["content"].get("text", "")
        metadata = ingest_result["content"].get("metadata", {})
        
        # Update Document with OCR info if available
        is_scanned = metadata.get("is_scanned", False)
        ocr_confidence = metadata.get("ocr_confidence")
        await self._update_document_ocr_info(document_id, is_scanned, ocr_confidence)

        # Step 2: Chunk text
        transform_result = await self._get_data_agent().process({
            "task_type": "transform",
            "content": raw_text,
            "chunk_size": message.get("chunk_size", 1000),
        })
        if not transform_result.get("success"):
            return transform_result

        chunks = transform_result["chunks"]

        # Step 3: Generate embeddings and store in vector DB
        embed_result = await self.analysis_agent.process({
            "task_type": "embed",
            "chunks": chunks,
            "metadata": {
                "document_id": document_id,
                "document_path": ingest_result["stored_path"],
                "filename": message.get("filename"),
                "user_id": message.get("user_id", "unknown"),  # NEW: For tenant isolation
            },
        })
        if not embed_result.get("success"):
            return embed_result

        # Step 4: Persist chunks to PostgreSQL
        vector_ids = embed_result.get("vector_ids", [])
        await self._store_chunks_to_db(document_id, chunks, vector_ids)

        # Step 5: Generate and store summary
        summary = ""
        try:
            summary_result = await self.analysis_agent.process({
                "task_type": "summarize",
                "content": raw_text[:15000],  # limit to avoid token overflow
            })
            if summary_result.get("success"):
                summary = summary_result.get("summary", "")
        except Exception as e:
            logger.warning(f"Summary generation failed (non-fatal): {e}")

        # Step 6: Track progress
        await self.planning_agent.process({
            "task_type": "track_progress",
            "task_id": message.get("task_id"),
            "progress_data": {
                "step": "completed",
                "chunks_processed": transform_result["chunk_count"],
                "embeddings_created": embed_result["embedding_count"],
                "summary_generated": bool(summary),
            },
        })

        self.log_event("workflow_complete", {
            "workflow_type": "ingest_and_analyze",
            "chunks_processed": transform_result["chunk_count"],
        })

        return {
            "success": True,
            "workflow_type": "ingest_and_analyze",
            "document_id": document_id,
            "document_path": ingest_result["stored_path"],
            "chunks_processed": transform_result["chunk_count"],
            "vector_ids": vector_ids,
            "summary": summary,
            "agent_id": self.agent_id,
        }

    async def _store_chunks_to_db(self, document_id: str, chunks: list, vector_ids: list):
        """Persist document chunks to PostgreSQL."""
        try:
            from backend.models import get_db, DocumentChunk

            db = next(get_db())
            for i, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk_text,
                    milvus_id=vector_ids[i] if i < len(vector_ids) else None,
                )
                db.add(chunk)
            db.commit()
            logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to store chunks to DB: {e}")

    async def _update_document_ocr_info(self, document_id: str, is_scanned: bool, ocr_confidence: float):
        """Update the Document record with OCR information."""
        try:
            from backend.models import get_db, Document
            
            db = next(get_db())
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.is_scanned = is_scanned
                doc.ocr_confidence = ocr_confidence
                db.commit()
                logger.info(f"Updated document {document_id} OCR info: is_scanned={is_scanned}, conf={ocr_confidence}")
        except Exception as e:
            logger.error(f"Failed to update document OCR info: {e}")

    async def process_query(self, query_text: str, user_id: str = None) -> Dict[str, Any]:
        """Process a query using RAG pipeline (Hybrid Search + Reranker + LLM).
        
        This is the main entry point for the /query endpoint.
        Args:
            query_text: The user's query
            user_id: Optional user ID for filtering results to user's documents only
        Returns: {"answer": str, "sources": [{"content": str, "metadata": dict, "score": float}]}
        """
        try:
            self.log_event("query_start", {"query": query_text, "user_id": user_id})
            
            # Step 1: Hybrid Vector Search (Dense + Sparse) with user filter
            from backend.utils.embeddings import get_embedding_engine
            embedding_engine = get_embedding_engine()
            search_results = await embedding_engine.search(query_text, top_k=20, user_id=user_id)
            
            # Step 2: Rerank top candidates
            from backend.utils.reranker import get_reranker
            reranker = get_reranker()
            reranked_results = reranker.rerank(query_text, search_results, top_n=5)
            
            # Step 3: Generate answer using RAG
            context_chunks = [r["text"] for r in reranked_results]
            # Use the LLMClient from AnalysisAgent (which has the api_key)
            answer = await self.analysis_agent.llm_client.generate_rag_response(query_text, context_chunks)
            
            # Format sources for response
            sources = [
                {
                    "content": r["text"],
                    "metadata": r.get("metadata", {}),
                    "score": r.get("score", 0.0)
                }
                for r in reranked_results
            ]
            
            self.log_event("query_complete", {"query": query_text, "sources_count": len(sources)})
            
            return {
                "success": True,
                "answer": answer,
                "sources": sources,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return {
                "success": False,
                "answer": "I encountered an error processing your query. Please try again.",
                "sources": [],
                "error": str(e)
            }

    async def _query_workflow(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Execute RAG query workflow (legacy method, delegates to process_query)."""
        query_text = message.get("query_text")
        user_id = message.get("user_id")
        return await self.process_query(query_text, user_id=user_id)
