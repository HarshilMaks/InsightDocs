"""API endpoints for querying and RAG."""
import time
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import logging
from backend.api.schemas import QueryRequest, QueryResponse, SourceReference
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
    """Query documents using RAG (authenticated users only, searches their documents)."""
    start = time.time()
    try:
        logger.info(f"Query by user {current_user.id}: {query_request.query}")
        
        # Use Orchestrator Agent (handles RAG, hybrid search, reranking, and generation internally)
        orchestrator = _get_user_orchestrator(current_user)
        result = await orchestrator.process_query(query_request.query, user_id=current_user.id)
        if not result.get("success"):
            error_msg = result.get("error", "Query processing failed")
            logger.error(f"Query workflow failed for user {current_user.id}: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        answer = result.get("answer", "")
        sources_data = result.get("sources", [])
        
        # Output guardrail is handled within Orchestrator/LLM Client potentially, 
        # or can be re-enabled here if check_output is updated to support BYOK.
        
        elapsed = round(time.time() - start, 3)

        # Build source references
        sources = []
        for s in sources_data:
            doc_id = s.get("metadata", {}).get("document_id")
            if not doc_id:
                continue
            
            doc = db.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == current_user.id,
            ).first()
            
            if doc:
                sources.append(SourceReference(
                    document_id=doc_id,
                    document_name=doc.filename,
                    content_preview=s.get("content", "")[:200],
                    similarity_score=s.get("score", 0.0),
                ))

        # Persist query record
        query_record = QueryModel(
            query_text=query_request.query,
            response_text=answer,
            response_time=elapsed,
            sources=[s.get("metadata", {}) for s in sources_data],
            user_id=current_user.id,
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)

        return QueryResponse(
            answer=answer,
            sources=sources,
            query_id=query_record.id,
            query=query_request.query,
            response_time=elapsed,
            confidence_score=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_query_history(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get query history for authenticated user."""
    try:
        queries = db.query(QueryModel).filter(
            QueryModel.user_id == current_user.id
        ).order_by(
            QueryModel.created_at.desc()
        ).offset(skip).limit(limit).all()

        return {
            "queries": [
                {
                    "id": q.id,
                    "query": q.query_text,
                    "response": q.response_text,
                    "response_time": q.response_time,
                    "created_at": q.created_at.isoformat(),
                }
                for q in queries
            ],
            "total": db.query(QueryModel).filter(QueryModel.user_id == current_user.id).count(),
        }
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
