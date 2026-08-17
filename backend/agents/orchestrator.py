"""Orchestrator Agent for coordinating all sub-agents."""
from typing import Dict, Any, List, Optional, Tuple
import logging
from sqlalchemy.orm import Session
from backend.core import BaseAgent
from backend.agents.data_agent import DataAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.models import get_db, Document, DocumentChunk, Query as QueryModel
from backend.utils.llm_client import GeminiAPIError

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Central orchestrator coordinating all sub-agents."""

    def __init__(self, agent_id: str = "orchestrator", api_key: str = None):
        super().__init__(agent_id, "OrchestratorAgent")
        self.data_agent = None
        self.analysis_agent = AnalysisAgent(api_key=api_key)

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
        s3_key = message.get("s3_key")

        # Step 1: Parse the already-uploaded document (worker downloaded its
        # own local copy before calling this workflow; see backend/workers/tasks.py)
        ingest_result = await self._get_data_agent().process({
            "task_type": "ingest",
            "file_path": message.get("file_path"),
            "filename": message.get("filename"),
            "s3_key": s3_key,
        })
        if not ingest_result.get("success"):
            return ingest_result

        raw_text = ingest_result["content"].get("text", "")
        metadata = ingest_result["content"].get("metadata", {})
        
        # Update Document with OCR info if available
        is_scanned = metadata.get("is_scanned", False)
        ocr_confidence = metadata.get("ocr_confidence")
        await self._update_document_ocr_info(document_id, is_scanned, ocr_confidence)

        # Step 2: Chunk text (pass the full parsed content, not just raw
        # text, so spatial blocks and tables reach the chunker and enable
        # section-aware, table-atomic chunking with parent-child linkage)
        transform_result = await self._get_data_agent().process({
            "task_type": "transform",
            "content": ingest_result["content"],
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

        # Step 4: Persist chunks to PostgreSQL. This is fatal: a document
        # with vectors in Milvus but no corresponding DocumentChunk rows
        # cannot be cited, so treat the failure as a workflow failure rather
        # than continuing silently.
        vector_ids = embed_result.get("vector_ids", [])
        try:
            await self._store_chunks_to_db(document_id, chunks, vector_ids)
        except Exception as e:
            logger.error(f"Fatal: failed to persist chunks for document {document_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to persist document chunks: {e}",
                "workflow_type": "ingest_and_analyze",
                "document_id": document_id,
            }

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

        # Step 5.5 + Step 6 (removed): PlanningAgent next-steps and
        # track_progress calls added a blocking Gemini call per ingestion
        # for near-zero product value. Removed to reduce processing time.

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
        """Persist document chunks to PostgreSQL with optional bbox and
        structural metadata (section title, chunk type, parent linkage).

        Chunks produced by the section/table-aware chunker
        (EnhancedPDFParser.chunk_blocks) may reference a parent chunk by its
        position in the `chunks` list via `parent_chunk_index`. Since
        PostgreSQL parent_chunk_id is a foreign key to a real row id (not a
        list position), parent chunks are inserted first so their generated
        ids are known before child rows are created.

        Raises on failure instead of swallowing the exception: callers must
        treat chunk-persistence failure as fatal to the ingestion workflow,
        since a chunk that exists only as a Milvus vector with no PostgreSQL
        row can never be hydrated into a citation.
        """
        from backend.models import get_db, DocumentChunk

        db_gen = get_db()
        db = next(db_gen)
        try:
            # Resolve each chunk's parent_chunk_index (a position in
            # `chunks`) to the DB row id of that parent, once it has been
            # inserted. Parents are recognized by is_parent=True and have no
            # parent of their own (parent_chunk_index is always None for a
            # parent chunk itself, by construction in chunk_blocks()).
            index_to_db_id: Dict[int, str] = {}

            def _extract_fields(chunk_data):
                if isinstance(chunk_data, str):
                    return {
                        "text": chunk_data,
                        "bbox": None,
                        "page_number": None,
                        "section_title": None,
                        "chunk_type": None,
                        "parent_chunk_index": None,
                        "is_parent": False,
                    }
                return {
                    "text": chunk_data.get("text", ""),
                    "bbox": chunk_data.get("bbox"),
                    "page_number": chunk_data.get("page_number"),
                    "section_title": chunk_data.get("section_title"),
                    "chunk_type": chunk_data.get("chunk_type"),
                    "parent_chunk_index": chunk_data.get("parent_chunk_index"),
                    "is_parent": bool(chunk_data.get("is_parent", False)),
                }

            parsed = [_extract_fields(c) for c in chunks]

            # Pass 1: insert parent chunks (and any chunk with no parent
            # reference) so they receive real ids before children are created.
            from backend.config import settings as app_settings
            for i, fields in enumerate(parsed):
                if not fields["is_parent"]:
                    continue
                bbox = fields["bbox"]
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=fields["text"],
                    milvus_id=vector_ids[i] if i < len(vector_ids) else None,
                    page_number=fields["page_number"],
                    bbox_x1=bbox["x1"] if bbox else None,
                    bbox_y1=bbox["y1"] if bbox else None,
                    bbox_x2=bbox["x2"] if bbox else None,
                    bbox_y2=bbox["y2"] if bbox else None,
                    section_title=fields["section_title"],
                    chunk_type=fields["chunk_type"] or "text",
                    parent_chunk_id=None,
                    embedding_model=app_settings.embedding_model_name,
                    embedding_dimension=768,
                )
                db.add(chunk)
                db.flush()  # assign chunk.id without committing the transaction
                index_to_db_id[i] = chunk.id

            # Pass 2: insert every remaining (non-parent) chunk, resolving
            # its parent_chunk_index to the parent's real DB id if present.
            for i, fields in enumerate(parsed):
                if fields["is_parent"]:
                    continue
                bbox = fields["bbox"]
                parent_idx = fields["parent_chunk_index"]
                parent_db_id = index_to_db_id.get(parent_idx) if parent_idx is not None else None
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=fields["text"],
                    milvus_id=vector_ids[i] if i < len(vector_ids) else None,
                    page_number=fields["page_number"],
                    bbox_x1=bbox["x1"] if bbox else None,
                    bbox_y1=bbox["y1"] if bbox else None,
                    bbox_x2=bbox["x2"] if bbox else None,
                    bbox_y2=bbox["y2"] if bbox else None,
                    section_title=fields["section_title"],
                    chunk_type=fields["chunk_type"] or "text",
                    parent_chunk_id=parent_db_id,
                    embedding_model=app_settings.embedding_model_name,
                    embedding_dimension=768,
                )
                db.add(chunk)

            db.commit()
            logger.info(
                f"Stored {len(chunks)} chunks for document {document_id} "
                f"(with bbox/section/table data where available)"
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db_gen.close()

    async def _update_document_ocr_info(self, document_id: str, is_scanned: bool, ocr_confidence: float):
        """Update the Document record with OCR information."""
        from backend.models import get_db, Document

        db_gen = get_db()
        db = next(db_gen)
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.is_scanned = is_scanned
                doc.ocr_confidence = ocr_confidence
                db.commit()
                logger.info(f"Updated document {document_id} OCR info: is_scanned={is_scanned}, conf={ocr_confidence}")
        except Exception as e:
            logger.error(f"Failed to update document OCR info: {e}")
        finally:
            db_gen.close()

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

    @staticmethod
    def _get_parent_context(
        chunk: Optional['DocumentChunk'],
        parent_chunks: Dict[str, 'DocumentChunk'],
    ) -> Optional[str]:
        """Return the parent chunk's content if it provides meaningfully
        wider context than the child chunk alone.

        The parent's text is the concatenation of an entire section, so
        feeding it alongside the child gives the LLM broader context for
        generation while the citation still points at the precise child.
        Returns None when no parent exists or the parent adds negligible
        extra content (less than 1.5x the child's length).
        """
        if chunk is None or not chunk.parent_chunk_id:
            return None
        parent = parent_chunks.get(chunk.parent_chunk_id)
        if parent is None or not parent.content:
            return None
        # Only include parent context if it is meaningfully larger than
        # the child chunk itself (avoids redundant duplication).
        if len(parent.content) < len(chunk.content) * 1.5:
            return None
        return parent.content

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

            # Batch-fetch parent chunks so we can provide wider section
            # context to the LLM while citing the precise child chunk.
            parent_ids = {
                chunk.parent_chunk_id
                for chunk in chunks.values()
                if chunk.parent_chunk_id
            }
            parent_chunks: Dict[str, DocumentChunk] = {}
            if parent_ids:
                parent_rows = (
                    db.query(DocumentChunk)
                    .filter(DocumentChunk.id.in_(parent_ids))
                    .all()
                )
                parent_chunks = {p.id: p for p in parent_rows}

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
                    section_title = chunk.section_title
                    chunk_type = chunk.chunk_type or "text"
                else:
                    document_name = metadata.get("document_name") or (document.filename if document else "Document")
                    page_number = metadata.get("page_number")
                    raw_chunk_index = metadata.get("chunk_index")
                    chunk_index = raw_chunk_index + 1 if isinstance(raw_chunk_index, int) else source_number
                    chunk_id = str(result.get("id", ""))
                    bbox = metadata.get("bbox")
                    document_id = metadata.get("document_id", "")
                    section_title = metadata.get("section_title")
                    chunk_type = metadata.get("chunk_type", "text")

                citation = {
                    "source_number": source_number,
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "bbox": bbox,
                    "section_title": section_title,
                    "chunk_type": chunk_type,
                    "citation_label": self._build_citation_label(document_name, page_number, chunk_index),
                }

                citation_context.append({
                    "text": result.get("text", ""),
                    "citation": citation,
                    "parent_context": self._get_parent_context(chunk, parent_chunks) if chunk else None,
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
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a query using RAG pipeline (Hybrid Search + Reranker + LLM).
        
        This is the main entry point for the /query endpoint.
        Args:
            query_text: The user's query
            user_id: Required user ID for strict tenant isolation
            document_id: Optional document ID to scope retrieval to a single
                document (e.g. the document workspace view). The document
                must be owned by user_id; otherwise the scope is ignored and
                retrieval falls back to searching all of the user's documents.
        Returns: {"answer": str, "sources": [{"content": str, "metadata": dict, "score": float}]}
        """
        db_gen = None
        if db is None:
            db_gen = get_db()
            db = next(db_gen)
        try:
            top_k = max(1, top_k)
            history_limit = max(0, history_limit)
            if not user_id:
                raise ValueError("user_id is required for tenant-isolated queries")

            scoped_document_id = None
            if document_id:
                owns_document = (
                    db.query(Document)
                    .filter(Document.id == document_id, Document.user_id == user_id)
                    .first()
                )
                if owns_document:
                    scoped_document_id = document_id
                else:
                    logger.warning(
                        f"User {user_id} requested document scope {document_id} "
                        "they do not own; ignoring scope."
                    )

            self.log_event("query_start", {"query": query_text, "user_id": user_id, "document_id": scoped_document_id})
            
            # Step 1: Hybrid Vector Search (Dense + Sparse) with user filter
            from backend.utils.embeddings import get_embedding_engine
            embedding_engine = get_embedding_engine()
            search_top_k = max(top_k * 4, 20)
            search_results = await embedding_engine.search(
                query_text,
                top_k=search_top_k,
                user_id=user_id,
                document_id=scoped_document_id,
            )
            
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

            # Step 3.5: Verify each factual claim in the answer against the
            # retrieved sources. This runs inline (synchronously, before the
            # response is returned) rather than deferred asynchronously —
            # a known limitation documented in the roadmap: if verification
            # is slow, it adds directly to query latency. It fails open
            # (returns None) rather than blocking or corrupting the answer
            # if the Gemini call or JSON parsing fails.
            claim_verifications = None
            try:
                from backend.middleware.guardrails import verify_claims
                claim_verifications = verify_claims(
                    answer,
                    context_chunks,
                    api_key=self.analysis_agent.llm_client.api_key,
                )
            except Exception as e:
                logger.warning(f"Claim verification failed (non-fatal): {e}")

            # Step 4 (removed): PlanningAgent next-steps generation was here
            # but added a blocking Gemini call per query for near-zero
            # product value. Removed to reduce query latency and cost.
            
            self.log_event("query_complete", {"query": query_text, "sources_count": len(sources)})
            
            return {
                "success": True,
                "answer": answer,
                "sources": sources,
                "conversation_history": conversation_history,
                "claim_verifications": claim_verifications,
                "agent_id": self.agent_id
            }
        except GeminiAPIError as e:
            logger.warning(f"Gemini query failed for user {user_id}: {e}")
            return {
                "success": False,
                "answer": "",
                "sources": [],
                "error": str(e),
                "error_type": type(e).__name__,
                "error_code": getattr(e, "error_code", type(e).__name__),
                "status_code": getattr(e, "status_code", 503),
                "attempts": getattr(e, "attempts", []),
                "active_model": getattr(e, "active_model", None),
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
            document_id=message.get("document_id"),
        )
