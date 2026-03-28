"""API endpoints for querying and RAG."""
import time
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import logging
from backend.api.schemas import (
    BoundingBox,
    QueryHistoryResponse,
    QueryRequest,
    QueryResponse,
    SourceReference,
)
from backend.models import get_db, Query as QueryModel, Document
from backend.models.schemas import User
from backend.core.security import get_current_user, decrypt_api_key
from backend.agents.orchestrator import OrchestratorAgent
from backend.core.limiter import limiter
from backend.middleware.guardrails import check_input_guardrail

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Query"])

def _get_user_orchestrator(current_user: User) -> OrchestratorAgent:
    """Helper to initialize OrchestratorAgent with user's API key if present."""
    api_key = None
    if current_user.byok_enabled and current_user.gemini_api_key_encrypted:
        try:
            api_key = decrypt_api_key(current_user.gemini_api_key_encrypted)
        except Exception:
            logger.error(f"Failed to decrypt API key for user {current_user.id}")
            pass
    return OrchestratorAgent(api_key=api_key)

@router.post("/", response_model=QueryResponse, dependencies=[Depends(check_input_guardrail)])
@limiter.limit("10/minute")
async def query_documents(
    request: Request,
    query_request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ask follow-up questions about the user's uploaded documents using RAG."""
    start = time.time()
    try:
        logger.info(f"Query by user {current_user.id}: {query_request.query}")
        conversation_id = query_request.conversation_id or str(uuid4())
        turn_index = (
            db.query(QueryModel)
            .filter(
                QueryModel.user_id == current_user.id,
                QueryModel.conversation_id == conversation_id,
            )
            .count()
            + 1
        )
        
        # Use Orchestrator Agent (handles RAG, hybrid search, reranking, and generation internally)
        orchestrator = _get_user_orchestrator(current_user)
        result = await orchestrator.process_query(
            query_request.query,
            user_id=current_user.id,
            conversation_id=conversation_id,
            db=db,
            top_k=max(1, query_request.top_k or 5),
        )
        if not result.get("success"):
            error_msg = result.get("error", "Query processing failed")
            logger.error(f"Query workflow failed for user {current_user.id}: {error_msg}")
            raise HTTPException(
                status_code=int(result.get("status_code") or 500),
                detail=error_msg,
            )
        
        answer = result.get("answer", "")
        sources_data = result.get("sources", [])
        
        # Output guardrail is handled within Orchestrator/LLM Client potentially, 
        # or can be re-enabled here if check_output is updated to support BYOK.
        
        elapsed = round(time.time() - start, 3)

        # Build source references
        sources = []
        for s in sources_data:
            metadata = s.get("metadata", {}) or {}
            citation = metadata.get("citation", {}) or {}
            doc_id = citation.get("document_id") or metadata.get("document_id")
            if not doc_id:
                continue

            doc = db.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == current_user.id,
            ).first()
            if not doc:
                continue

            bbox_payload = citation.get("bbox")
            bbox = None
            if isinstance(bbox_payload, dict) and all(k in bbox_payload for k in ("x1", "y1", "x2", "y2")):
                bbox_data = dict(bbox_payload)
                bbox_data.setdefault("page_number", citation.get("page_number"))
                bbox = BoundingBox(**bbox_data)

            source_number = citation.get("source_number") or (len(sources) + 1)
            sources.append(SourceReference(
                source_number=source_number,
                document_id=doc_id,
                document_name=citation.get("document_name") or doc.filename,
                chunk_id=str(citation.get("chunk_id") or s.get("id") or ""),
                chunk_index=int(citation.get("chunk_index") or source_number),
                page_number=citation.get("page_number"),
                bbox=bbox,
                content_preview=s.get("content", "")[:200],
                similarity_score=s.get("score", 0.0),
                citation_label=citation.get("citation_label") or f"Source {source_number}",
            ))

        # Persist query record
        query_record = QueryModel(
            query_text=query_request.query,
            response_text=answer,
            response_time=elapsed,
            sources=sources_data,
            user_id=current_user.id,
            conversation_id=conversation_id,
            turn_index=turn_index,
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)

        return QueryResponse(
            answer=answer,
            sources=sources,
            query_id=query_record.id,
            conversation_id=conversation_id,
            turn_index=turn_index,
            query=query_request.query,
            response_time=elapsed,
            confidence_score=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=QueryHistoryResponse)
async def get_query_history(
    skip: int = 0,
    limit: int = 100,
    conversation_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get query history for authenticated user."""
    try:
        query = db.query(QueryModel).filter(QueryModel.user_id == current_user.id)
        if conversation_id:
            query = query.filter(QueryModel.conversation_id == conversation_id).order_by(
                QueryModel.turn_index.asc(),
                QueryModel.created_at.asc(),
            )
        else:
            query = query.order_by(QueryModel.created_at.desc())

        queries = query.offset(skip).limit(limit).all()
        total_query = db.query(QueryModel).filter(QueryModel.user_id == current_user.id)
        if conversation_id:
            total_query = total_query.filter(QueryModel.conversation_id == conversation_id)

        return {
            "queries": [
                {
                    "id": q.id,
                    "conversation_id": q.conversation_id,
                    "turn_index": q.turn_index,
                    "query": q.query_text,
                    "response": q.response_text,
                    "response_time": q.response_time,
                    "created_at": q.created_at.isoformat(),
                }
                for q in queries
            ],
            "total": total_query.count(),
        }
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
