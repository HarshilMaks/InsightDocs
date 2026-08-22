"""Owner-scoped human review APIs for persisted Evidence Gate audits.

This router is deliberately read-only with respect to query/audit evidence. Reviewers can
only append a decision while atomically advancing a run's review version. Source detail is
rebuilt from the query-time snapshot and then filtered through current document ownership.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from fastapi import APIRouter, Depends, HTTPException, Query as ApiQuery, status
from sqlalchemy import update
from sqlalchemy.orm import Session, selectinload

from backend.api.schemas import (
    BoundingBox,
    EvidenceGateReviewClaim,
    EvidenceGateReviewDecisionEvent,
    EvidenceGateReviewDecisionRequest,
    EvidenceGateReviewDetail,
    EvidenceGateReviewQueueItem,
    EvidenceGateReviewQueueResponse,
    EvidenceGateReviewSource,
)
from backend.core.security import get_current_user
from backend.models import (
    Document,
    EvidenceGateClaim,
    EvidenceGateReviewDecision,
    EvidenceGateRun,
    Query,
    User,
    get_db,
)


router = APIRouter(prefix="/evidence-gate", tags=["Evidence Gate Review"])


def _owned_run(db: Session, run_id: str, user_id: str) -> EvidenceGateRun:
    """Fetch an audit only through its query owner; conceal other tenants as 404."""
    run = (
        db.query(EvidenceGateRun)
        .join(Query, EvidenceGateRun.query_id == Query.id)
        .options(
            selectinload(EvidenceGateRun.claims),
            selectinload(EvidenceGateRun.review_decisions),
            selectinload(EvidenceGateRun.query),
        )
        .filter(EvidenceGateRun.id == run_id, Query.user_id == user_id)
        .one_or_none()
    )
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found.")
    return run


def _source_number(value: Any, fallback: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return fallback


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, bool):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    try:
        if isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _snapshot_sources(db: Session, query: Query, user_id: str) -> dict[int, EvidenceGateReviewSource]:
    """Hydrate the frozen query snapshot, filtering every document by present ownership.

    The snapshot supplies citation/content fields. Current document lookup supplies the
    authoritative display name and rejects deleted or cross-tenant document references.
    No client-supplied source/document identifiers participate in this process.
    """
    raw_sources = query.sources if isinstance(query.sources, list) else []
    parsed: list[tuple[int, Mapping[str, Any], Mapping[str, Any], str]] = []
    document_ids: set[str] = set()

    for index, raw_source in enumerate(raw_sources, start=1):
        if not isinstance(raw_source, Mapping):
            continue
        metadata = raw_source.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        citation = metadata.get("citation")
        citation = citation if isinstance(citation, Mapping) else {}
        document_id = citation.get("document_id") or metadata.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            continue
        source_number = _source_number(citation.get("source_number"), index)
        parsed.append((source_number, raw_source, citation, document_id))
        document_ids.add(document_id)

    if not document_ids:
        return {}
    documents = {
        document.id: document
        for document in (
            db.query(Document)
            .filter(Document.user_id == user_id, Document.id.in_(document_ids))
            .all()
        )
    }

    sources: dict[int, EvidenceGateReviewSource] = {}
    for source_number, raw_source, citation, document_id in parsed:
        # Keep the first snapshot item for a source number, matching query-response
        # numbering and preventing duplicate/untrusted snapshot aliases.
        if source_number in sources:
            continue
        document = documents.get(document_id)
        if document is None:
            continue
        bbox = citation.get("bbox")
        bbox_model = None
        if isinstance(bbox, Mapping) and all(key in bbox for key in ("x1", "y1", "x2", "y2")):
            bbox_model = BoundingBox(
                x1=_number(bbox.get("x1")),
                y1=_number(bbox.get("y1")),
                x2=_number(bbox.get("x2")),
                y2=_number(bbox.get("y2")),
                page_number=_integer(citation.get("page_number"), 0) or None,
            )
        content = raw_source.get("content")
        sources[source_number] = EvidenceGateReviewSource(
            source_number=source_number,
            document_id=document.id,
            document_name=document.filename,
            chunk_id=str(citation.get("chunk_id") or raw_source.get("id") or ""),
            chunk_index=_integer(citation.get("chunk_index"), source_number),
            page_number=_integer(citation.get("page_number"), 0) or None,
            bbox=bbox_model,
            section_title=(
                citation.get("section_title") if isinstance(citation.get("section_title"), str) else None
            ),
            chunk_type=(
                citation.get("chunk_type")
                if isinstance(citation.get("chunk_type"), str)
                else "text"
            ),
            content=content if isinstance(content, str) else "",
            similarity_score=_number(raw_source.get("score")),
            citation_label=(
                citation.get("citation_label")
                if isinstance(citation.get("citation_label"), str)
                else f"Source {source_number}"
            ),
        )
    return sources


def _history(run: EvidenceGateRun) -> list[EvidenceGateReviewDecisionEvent]:
    return [
        EvidenceGateReviewDecisionEvent(
            id=event.id,
            reviewer_id=event.reviewer_id,
            decision=event.decision,
            note=event.note,
            expected_version=event.expected_version,
            result_version=event.result_version,
            created_at=event.created_at,
        )
        for event in sorted(run.review_decisions, key=lambda event: event.result_version)
    ]


def _detail(db: Session, run: EvidenceGateRun, user_id: str) -> EvidenceGateReviewDetail:
    snapshot_sources = _snapshot_sources(db, run.query, user_id)
    claims = []
    for claim in sorted(run.claims, key=lambda item: item.ordinal):
        source_numbers = [
            source_number
            for raw_number in (claim.supporting_source_numbers or [])
            if (source_number := _source_number(raw_number, 0)) > 0
        ]
        claims.append(
            EvidenceGateReviewClaim(
                id=claim.id,
                ordinal=claim.ordinal,
                claim_text=claim.claim_text,
                verdict=claim.verdict,
                reason=claim.reason,
                supporting_source_numbers=source_numbers,
                sources=[
                    snapshot_sources[source_number]
                    for source_number in source_numbers
                    if source_number in snapshot_sources
                ],
            )
        )
    return EvidenceGateReviewDetail(
        id=run.id,
        query_id=run.query_id,
        query_text=run.query.query_text,
        response_text=run.query.response_text,
        policy_version=run.policy_version,
        mode=run.mode,
        status=run.status,
        action=run.action,
        review_status=run.review_status,
        review_version=run.review_version,
        reviewed_at=run.reviewed_at,
        created_at=run.created_at,
        claims=claims,
        decision_history=_history(run),
    )


@router.get("/reviews", response_model=EvidenceGateReviewQueueResponse)
def list_review_queue(
    review_status: Literal["pending", "accepted", "rejected"] = "pending",
    skip: int = ApiQuery(0, ge=0),
    limit: int = ApiQuery(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the authenticated owner's review queue without exposing other tenants."""
    base = (
        db.query(EvidenceGateRun, Query)
        .join(Query, EvidenceGateRun.query_id == Query.id)
        .filter(Query.user_id == current_user.id, EvidenceGateRun.review_status == review_status)
    )
    total = base.count()
    rows = (
        base.order_by(EvidenceGateRun.created_at.desc(), EvidenceGateRun.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return EvidenceGateReviewQueueResponse(
        total=total,
        items=[
            EvidenceGateReviewQueueItem(
                id=run.id,
                query_id=run.query_id,
                query_text=query.query_text,
                status=run.status,
                claim_count=run.claim_count,
                unsupported_count=run.unsupported_count,
                unverified_count=run.unverified_count,
                review_status=run.review_status,
                review_version=run.review_version,
                created_at=run.created_at,
            )
            for run, query in rows
        ],
    )


@router.get("/reviews/{run_id}", response_model=EvidenceGateReviewDetail)
def get_review_detail(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return an owner-scoped review item and its snapshot-derived evidence."""
    return _detail(db, _owned_run(db, run_id, current_user.id), current_user.id)


@router.post("/reviews/{run_id}/decisions", response_model=EvidenceGateReviewDetail)
def create_review_decision(
    run_id: str,
    payload: EvidenceGateReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Append a decision only when the caller's review version is current."""
    run = _owned_run(db, run_id, current_user.id)
    now = datetime.now(timezone.utc)
    update_result = db.execute(
        update(EvidenceGateRun)
        .where(
            EvidenceGateRun.id == run.id,
            EvidenceGateRun.review_version == payload.expected_version,
        )
        .values(
            review_status=payload.decision,
            review_version=EvidenceGateRun.review_version + 1,
            reviewed_at=now,
        )
    )
    if update_result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review decision is stale; refresh and retry.",
        )

    note = payload.note.strip() if payload.note else None
    db.add(
        EvidenceGateReviewDecision(
            gate_run_id=run.id,
            reviewer_id=current_user.id,
            decision=payload.decision,
            note=note or None,
            expected_version=payload.expected_version,
            result_version=payload.expected_version + 1,
        )
    )
    db.commit()
    # The compare-and-swap update bypasses the identity map, so reload the
    # authoritative row plus its just-appended immutable event before responding.
    db.expire_all()
    return _detail(db, _owned_run(db, run_id, current_user.id), current_user.id)
