"""Orchestrator Agent for coordinating all sub-agents."""
from typing import Dict, Any, List, Optional, Tuple
import logging
from sqlalchemy.orm import Session
from backend.core import BaseAgent
from backend.agents.data_agent import DataAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.planning_agent import PlanningAgent
from backend.models import get_db, Document, DocumentChunk, Query as QueryModel

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

        await self._update_document_storage_info(
            document_id,
            self._get_data_agent().file_storage.bucket_name,
            ingest_result["stored_path"],
        )

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
        """Persist document chunks to PostgreSQL with optional bbox data."""
        try:
            from backend.models import get_db, DocumentChunk

            db = next(get_db())
            for i, chunk_data in enumerate(chunks):
                # Handle both old format (str) and new format (dict with bbox)
                if isinstance(chunk_data, str):
                    chunk_text = chunk_data
                    bbox = None
                    page_number = None
                else:
                    chunk_text = chunk_data.get("text", "")
                    bbox = chunk_data.get("bbox")
                    page_number = chunk_data.get("page_number")
                
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk_text,
                    milvus_id=vector_ids[i] if i < len(vector_ids) else None,
                    page_number=page_number,
                    bbox_x1=bbox["x1"] if bbox else None,
                    bbox_y1=bbox["y1"] if bbox else None,
                    bbox_x2=bbox["x2"] if bbox else None,
                    bbox_y2=bbox["y2"] if bbox else None,
                )
                db.add(chunk)
            db.commit()
            logger.info(f"Stored {len(chunks)} chunks for document {document_id} (with bbox data where available)")
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

    async def _update_document_storage_info(self, document_id: str, s3_bucket: str, s3_key: str):
        """Update the Document record with the final object storage location."""
        try:
            db = next(get_db())
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.s3_bucket = s3_bucket
                doc.s3_key = s3_key
                db.commit()
                logger.info(
                    f"Updated document {document_id} storage info: bucket={s3_bucket}, key={s3_key}"
                )
        except Exception as e:
            logger.error(f"Failed to update document storage info: {e}")

    @staticmethod
    def _build_bbox_payload(chunk: DocumentChunk) -> Optional[Dict[str, float]]:
        """Convert chunk bbox columns into an API-friendly payload."""
        if None in (chunk.bbox_x1, chunk.bbox_y1, chunk.bbox_x2, chunk.bbox_y2):
            return None
        return {
            "x1": float(chunk.bbox_x1),
            "y1": float(chunk.bbox_y1),
            "x2": float(chunk.bbox_x2),
            "y2": float(chunk.bbox_y2),
        }

    @staticmethod
    def _build_citation_label(document_name: str, page_number: Optional[int], chunk_index: Optional[int]) -> str:
        """Create a human-readable citation label."""
        parts: List[str] = []
        if document_name:
            parts.append(document_name)
        if page_number is not None:
            parts.append(f"Page {page_number}")
        if chunk_index is not None:
            parts.append(f"Chunk {chunk_index}")
        return " · ".join(parts) if parts else "Source"

    def _hydrate_citations(
        self,
        reranked_results: List[Dict[str, Any]],
        user_id: str,
        db: Optional[Session] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Attach document/page/chunk metadata to each retrieved result."""
        db_gen = None
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
        try:
            document_ids = {
                result.get("metadata", {}).get("document_id")
                for result in reranked_results
                if result.get("metadata", {}).get("document_id")
            }
            chunk_ids = [result.get("id") for result in reranked_results if result.get("id")]

            documents = {}
            if document_ids:
                docs = db.query(Document).filter(
                    Document.user_id == user_id,
                    Document.id.in_(document_ids),
                ).all()
                documents = {doc.id: doc for doc in docs}

            chunks = {}
            if chunk_ids:
                chunk_rows = (
                    db.query(DocumentChunk)
                    .join(Document)
                    .filter(
                        Document.user_id == user_id,
                        DocumentChunk.milvus_id.in_(chunk_ids),
                    )
                    .all()
                )
                chunks = {chunk.milvus_id: chunk for chunk in chunk_rows}

            citation_context: List[Dict[str, Any]] = []
            enriched_sources: List[Dict[str, Any]] = []

            for source_number, result in enumerate(reranked_results, start=1):
                metadata = dict(result.get("metadata") or {})
                chunk = chunks.get(result.get("id"))
                document = documents.get(metadata.get("document_id"))

                if chunk is not None:
                    document = document or chunk.document
                    document_name = document.filename if document else metadata.get("document_name", "Document")
                    page_number = chunk.page_number
                    chunk_index = chunk.chunk_index + 1
                    chunk_id = chunk.id
                    bbox = self._build_bbox_payload(chunk)
                    document_id = chunk.document_id
                else:
                    document_name = metadata.get("document_name") or (document.filename if document else "Document")
                    page_number = metadata.get("page_number")
                    raw_chunk_index = metadata.get("chunk_index")
                    chunk_index = raw_chunk_index + 1 if isinstance(raw_chunk_index, int) else source_number
                    chunk_id = str(result.get("id", ""))
                    bbox = metadata.get("bbox")
                    document_id = metadata.get("document_id", "")

                citation = {
                    "source_number": source_number,
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "bbox": bbox,
                    "citation_label": self._build_citation_label(document_name, page_number, chunk_index),
                }

                citation_context.append({
                    "text": result.get("text", ""),
                    "citation": citation,
                })
                enriched_sources.append({
                    "content": result.get("text", ""),
                    "metadata": {
                        **metadata,
                        "citation": citation,
                    },
                    "score": result.get("score", 0.0),
                    "source_number": source_number,
                })

            return citation_context, enriched_sources
        finally:
            if db_gen is not None:
                db_gen.close()

    @staticmethod
    def _build_conversation_history(
        db: Session,
        user_id: str,
        conversation_id: Optional[str],
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """Load recent turns for a chat thread so follow-up questions stay grounded."""
        if not conversation_id:
            return []

        prior_turns = (
            db.query(QueryModel)
            .filter(
                QueryModel.user_id == user_id,
                QueryModel.conversation_id == conversation_id,
            )
            .order_by(QueryModel.created_at.desc())
            .limit(limit)
            .all()
        )

        conversation_history: List[Dict[str, Any]] = []
        for turn in reversed(prior_turns):
            conversation_history.append(
                {
                    "query": turn.query_text,
                    "response": turn.response_text or "",
                    "turn_index": turn.turn_index,
                }
            )
        return conversation_history

    async def process_query(
        self,
        query_text: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        db: Optional[Session] = None,
        top_k: int = 5,
        history_limit: int = 4,
    ) -> Dict[str, Any]:
        """Process a query using RAG pipeline (Hybrid Search + Reranker + LLM).
        
        This is the main entry point for the /query endpoint.
        Args:
            query_text: The user's query
            user_id: Required user ID for strict tenant isolation
        Returns: {"answer": str, "sources": [{"content": str, "metadata": dict, "score": float}]}
        """
        db_gen = None
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
        try:
            if not user_id:
                raise ValueError("user_id is required for tenant-isolated queries")

            self.log_event("query_start", {"query": query_text, "user_id": user_id})
            
            # Step 1: Hybrid Vector Search (Dense + Sparse) with user filter
            from backend.utils.embeddings import get_embedding_engine
            embedding_engine = get_embedding_engine()
            search_top_k = max(top_k * 4, 20)
            search_results = await embedding_engine.search(query_text, top_k=search_top_k, user_id=user_id)
            
            # Step 2: Rerank top candidates
            from backend.utils.reranker import get_reranker
            reranker = get_reranker()
            reranked_results = reranker.rerank(query_text, search_results, top_n=top_k)
            
            # Step 3: Generate answer using RAG
            conversation_history = self._build_conversation_history(db, user_id, conversation_id, history_limit)
            context_chunks, sources = self._hydrate_citations(reranked_results, user_id, db=db)

            # Use the LLMClient from AnalysisAgent (which has the api_key)
            answer = await self.analysis_agent.llm_client.generate_rag_response(
                query_text,
                context_chunks,
                conversation_history=conversation_history,
            )
            
            self.log_event("query_complete", {"query": query_text, "sources_count": len(sources)})
            
            return {
                "success": True,
                "answer": answer,
                "sources": sources,
                "conversation_history": conversation_history,
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
        finally:
            if db_gen is not None:
                db_gen.close()

    async def _query_workflow(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Execute RAG query workflow (legacy method, delegates to process_query)."""
        query_text = message.get("query_text")
        user_id = message.get("user_id")
        if not user_id:
            return {
                "success": False,
                "answer": "",
                "sources": [],
                "error": "user_id is required for tenant-isolated queries",
            }
        if not query_text:
            return {
                "success": False,
                "answer": "",
                "sources": [],
                "error": "query_text is required",
            }
        return await self.process_query(
            query_text,
            user_id=user_id,
            conversation_id=message.get("conversation_id"),
            top_k=message.get("top_k", 5),
        )
