"""API endpoints for querying and RAG."""
import time
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from backend.api.schemas import QueryRequest, QueryResponse, SourceReference
from backend.models import get_db, Query as QueryModel, DocumentChunk, Document
from backend.utils.embeddings import get_embedding_engine
from backend.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Query documents using RAG."""
    start = time.time()
    try:
        logger.info(f"Processing query: {request.query}")

        embedding_engine = get_embedding_engine()
        llm_client = LLMClient()

        # Vector search
        search_results = await embedding_engine.search(request.query, top_k=request.top_k)
        context_chunks = [r["text"] for r in search_results]

        # Generate answer
        answer = await llm_client.generate_rag_response(request.query, context_chunks)

        elapsed = round(time.time() - start, 3)

        # Build source references
        sources = []
        for r in search_results:
            doc_id = r.get("metadata", {}).get("document_id", "")
            doc = db.query(Document).filter(Document.id == doc_id).first()
            sources.append(SourceReference(
                document_id=doc_id,
                document_name=doc.filename if doc else "unknown",
                content_preview=r["text"][:200],
                similarity_score=r.get("score", 0.0),
            ))

        # Persist query record
        query_record = QueryModel(
            query_text=request.query,
            response_text=answer,
            response_time=elapsed,
            sources=[r.get("metadata", {}) for r in search_results],
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)

        return QueryResponse(
            answer=answer,
            sources=sources,
            query_id=query_record.id,
            query=request.query,
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
    db: Session = Depends(get_db)
):
    """Get query history."""
    try:
        queries = db.query(QueryModel).order_by(
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
            "total": db.query(QueryModel).count(),
        }
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
