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

    def __init__(self, agent_id: str = "orchestrator"):
        super().__init__(agent_id, "OrchestratorAgent")
        self.data_agent = DataAgent()
        self.analysis_agent = AnalysisAgent()
        self.planning_agent = PlanningAgent()

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
        ingest_result = await self.data_agent.process({
            "task_type": "ingest",
            "file_path": message.get("file_path"),
            "filename": message.get("filename"),
        })
        if not ingest_result.get("success"):
            return ingest_result

        raw_text = ingest_result["content"].get("text", "")

        # Step 2: Chunk text
        transform_result = await self.data_agent.process({
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

    async def _query_workflow(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Execute RAG query workflow."""
        query_text = message.get("query_text")
        self.log_event("workflow_start", {"workflow_type": "query", "query": query_text})

        return {
            "success": True,
            "workflow_type": "query",
            "query": query_text,
            "answer": "Query processing workflow placeholder",
            "agent_id": self.agent_id,
        }
