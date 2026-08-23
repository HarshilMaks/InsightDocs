"""API endpoints for querying and RAG."""
import time
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session, selectinload
import logging
from backend.api.schemas import (
    BoundingBox,
    ClaimVerification,
    EvidenceGateSummary,
    QueryHistoryResponse,
    QueryRequest,
    QueryResponse,
    SourceReference,
)
from backend.models import (
    get_db,
    Query as QueryModel,
    Document,
    EvidenceWorkspace,
    EvidenceWorkspaceDocument,
    TaskStatus,
)
from backend.models.schemas import User
from backend.core.security import get_current_user, decrypt_api_key
from backend.core.limiter import limiter
from backend.middleware.guardrails import check_input_guardrail, check_output
from backend.evidence_gate.service import persist_shadow_audit, shadow_audit_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Query"])

def _get_user_orchestrator(current_user: User) -> "OrchestratorAgent":
    """Helper to initialize OrchestratorAgent with user's API key if present."""
    from backend.agents.orchestrator import OrchestratorAgent
    api_key = None
    if current_user.byok_enabled and current_user.gemini_api_key_encrypted:
        try:
            api_key = decrypt_api_key(current_user.gemini_api_key_encrypted)
        except Exception:
            logger.error(f"Failed to decrypt API key for user {current_user.id}")
            pass
    return OrchestratorAgent(api_key=api_key)

def _resolve_workspace_document_ids(
    db: Session,
    workspace_id: str,
    user_id: str,
) -> list[str]:
    workspace = (
        db.query(EvidenceWorkspace)
        .options(
            selectinload(EvidenceWorkspace.document_memberships).selectinload(
                EvidenceWorkspaceDocument.document
            )
        )
        .filter(EvidenceWorkspace.id == workspace_id, EvidenceWorkspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Evidence Workspace not found.")

    ready_document_ids = [
        membership.document.id
        for membership in workspace.document_memberships
        if membership.document is not None
        and membership.document.user_id == user_id
        and membership.document.status == TaskStatus.COMPLETED
    ]
    if not ready_document_ids:
        raise HTTPException(
            status_code=400,
            detail="Evidence Workspace has no ready documents. Add a completed document and try again.",
        )
    return ready_document_ids


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
        if query_request.document_id and query_request.workspace_id:
            raise HTTPException(
                status_code=422,
                detail="document_id and workspace_id cannot be used together.",
            )

        workspace_document_ids = None
        if query_request.workspace_id:
            workspace_document_ids = _resolve_workspace_document_ids(
                db,
                query_request.workspace_id,
                current_user.id,
            )

        logger.info(f"Query by user {current_user.id}: {query_request.query}")
        conversation_id = query_request.conversation_id or str(uuid4())
        if query_request.workspace_id:
            existing_workspace = (
                db.query(QueryModel.workspace_id)
                .filter(
                    QueryModel.user_id == current_user.id,
                    QueryModel.conversation_id == conversation_id,
                    QueryModel.workspace_id.isnot(None),
                )
                .first()
            )
            if existing_workspace and existing_workspace.workspace_id != query_request.workspace_id:
                raise HTTPException(
                    status_code=409,
                    detail="conversation_id is already scoped to a different Evidence Workspace.",
                )
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
            document_id=query_request.document_id,
            document_ids=workspace_document_ids,
        )
        if not result.get("success"):
            error_msg = result.get("error", "Query processing failed")
            logger.error(f"Query workflow failed for user {current_user.id}: {error_msg}")
            raise HTTPException(
                status_code=int(result.get("status_code") or 500),
                detail=error_msg,
            )
        
        candidate_answer = result.get("answer", "")
        answer = candidate_answer
        sources_data = result.get("sources", [])
        claim_verifications_data = result.get("claim_verifications")
        was_flagged = False

        # Output guardrail: check generated answer against context for
        # hallucination. Uses user's API key when BYOK is enabled.
        # Fails open (returns original answer) if the check cannot run.
        output_api_key = None
        if current_user.byok_enabled and current_user.gemini_api_key_encrypted:
            try:
                output_api_key = decrypt_api_key(current_user.gemini_api_key_encrypted)
            except Exception:
                pass
        context_texts = [s.get("content", "") for s in sources_data if s.get("content")]
        if answer and context_texts:
            answer, was_flagged = check_output(answer, context_texts, api_key=output_api_key)
            if was_flagged:
                logger.warning(f"Output guardrail flagged response for user {current_user.id}")
        
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
                section_title=citation.get("section_title"),
                chunk_type=citation.get("chunk_type", "text"),
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
            workspace_id=query_request.workspace_id,
            conversation_id=conversation_id,
            turn_index=turn_index,
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)

        # Shadow auditing is additive. The existing Query has already committed, so
        # a later audit failure rolls back only its own transaction and never blocks
        # or rewrites a successful answer. No summary is returned on that failure.
        audit_summary = None
        try:
            audit_run = persist_shadow_audit(
                db,
                query=query_record,
                user_id=current_user.id,
                candidate_answer=candidate_answer,
                delivered_answer=answer,
                source_snapshot=[source.model_dump(mode="json") for source in sources],
                claim_verifications=claim_verifications_data,
                output_guard_flagged=was_flagged,
            )
            db.commit()
            audit_summary = shadow_audit_summary(audit_run)
        except Exception:
            db.rollback()
            logger.exception("Evidence Gate shadow audit failed for query %s", query_record.id)

        claim_verifications = None
        if claim_verifications_data and candidate_answer == answer:
            claim_verifications = [
                ClaimVerification(
                    claim=c.get("claim", ""),
                    status=c.get("status", "unverified"),
                    supporting_sources=c.get("supporting_sources") or [],
                    reason=c.get("reason"),
                )
                for c in claim_verifications_data
            ]

        return QueryResponse(
            answer=answer,
            sources=sources,
            query_id=query_record.id,
            conversation_id=conversation_id,
            turn_index=turn_index,
            query=query_request.query,
            response_time=elapsed,
            confidence_score=None,
            claim_verifications=claim_verifications,
            evidence_gate=(
                EvidenceGateSummary(
                    id=audit_summary.id,
                    policy_version=audit_summary.policy_version,
                    mode=audit_summary.mode,
                    status=audit_summary.status,
                    action=audit_summary.action,
                    claim_count=audit_summary.claim_count,
                    supported_count=audit_summary.supported_count,
                    unsupported_count=audit_summary.unsupported_count,
                    unverified_count=audit_summary.unverified_count,
                    verified_at=audit_summary.verified_at,
                )
                if audit_summary is not None
                else None
            ),
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
