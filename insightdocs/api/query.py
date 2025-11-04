"""API endpoints for querying and RAG."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from insightdocs.api.schemas import QueryRequest, QueryResponse
from insightdocs.models import get_db, Query as QueryModel
from insightdocs.utils.embeddings import EmbeddingEngine
from insightdocs.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Query documents using RAG.
    
    Args:
        request: Query request
        db: Database session
        
    Returns:
        Query response with answer and sources
    """
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Initialize components
        embedding_engine = EmbeddingEngine()
        llm_client = LLMClient()
        
        # Search for relevant chunks
        search_results = await embedding_engine.search(
            request.query,
            top_k=request.top_k
        )
        
        # Extract context chunks
        context_chunks = [result["text"] for result in search_results]
        
        # Generate answer using LLM
        answer = await llm_client.generate_rag_response(
            request.query,
            context_chunks
        )
        
        # Prepare sources
        sources = [
            {
                "text": result["text"],
                "metadata": result.get("metadata", {}),
                "distance": result.get("distance", 0.0)
            }
            for result in search_results
        ]
        
        # Save query to database
        query_record = QueryModel(
            query_text=request.query,
            response=answer,
            context_documents=[r.get("metadata", {}) for r in search_results]
        )
        db.add(query_record)
        db.commit()
        
        logger.info(f"Query processed successfully: {request.query}")
        
        return QueryResponse(
            success=True,
            query=request.query,
            answer=answer,
            sources=sources,
            metadata={
                "top_k": request.top_k,
                "sources_count": len(sources)
            }
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
    """Get query history.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of past queries
    """
    try:
        queries = db.query(QueryModel).order_by(
            QueryModel.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        query_list = [
            {
                "id": q.id,
                "query": q.query_text,
                "response": q.response,
                "created_at": q.created_at.isoformat()
            }
            for q in queries
        ]
        
        return {
            "queries": query_list,
            "total": db.query(QueryModel).count()
        }
        
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
