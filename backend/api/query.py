"""API endpoints for querying and RAG."""
import time
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import logging
from backend.api.schemas import QueryRequest, QueryResponse, SourceReference
from backend.models import get_db, Query as QueryModel, DocumentChunk, Document
from backend.models.schemas import User
from backend.core.security import get_current_user
from backend.utils.embeddings import get_embedding_engine
from backend.utils.llm_client import LLMClient
from backend.utils.reranker import get_reranker
from backend.middleware.guardrails import check_output
from backend.core.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/", response_model=QueryResponse)
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

        embedding_engine = get_embedding_engine()
        llm_client = LLMClient()
        reranker = get_reranker()

        # Hybrid vector search (dense + sparse) — returns top-20 candidates
        search_results = await embedding_engine.search(query_request.query, top_k=20)

        # Rerank to find the best 5 chunks
        search_results = reranker.rerank(query_request.query, search_results, top_n=query_request.top_k)

        context_chunks = [r["text"] for r in search_results]

        # Generate answer
        answer = await llm_client.generate_rag_response(query_request.query, context_chunks)

        # Output guardrail: check for hallucinations
        answer, was_flagged = check_output(answer, context_chunks)

        elapsed = round(time.time() - start, 3)

        # Build source references - filter by current user's documents
        sources = []
        for r in search_results:
            doc_id = r.get("metadata", {}).get("document_id", "")
            doc = db.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == current_user.id  # Only include user's docs
            ).first()
            if doc:  # Only add sources the user owns
                sources.append(SourceReference(
                    document_id=doc_id,
                    document_name=doc.filename if doc else "unknown",
                    content_preview=r["text"][:200],
                    similarity_score=r.get("score", 0.0),
                ))

        # Persist query record
        query_record = QueryModel(
            query_text=query_request.query,
            response_text=answer,
            response_time=elapsed,
            sources=[r.get("metadata", {}) for r in search_results],
            user_id=current_user.id,  # Associate with current user
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
