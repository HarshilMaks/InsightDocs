"""Persistence coordinator for InsightDocs Evidence Gate shadow audits.

The coordinator consumes server-owned, already-hydrated query output. It never performs
retrieval, invokes an LLM, changes an answer, or commits a transaction; the caller owns
availability policy and transaction boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping, Sequence

from sqlalchemy.orm import Session

from backend.models import EvidenceGateClaim as EvidenceGateClaimModel
from backend.models import EvidenceGateRun, Query

from .contracts import (
    EvidenceGateClaim,
    EvidenceGateInput,
    EvidenceGateMode,
    EvidenceGateVerdict,
    EvidenceSource,
)
from .hashing import source_snapshot_sha256, text_sha256
from .policy import evaluate_evidence_gate


POLICY_VERSION = "evidence-gate/v1"


@dataclass(frozen=True)
class ShadowAuditSummary:
    """Safe, compact audit metadata suitable for an optional query response field."""

    id: str
    policy_version: str
    mode: str
    status: str
    action: str | None
    claim_count: int
    supported_count: int
    unsupported_count: int
    unverified_count: int
    verified_at: object


def persist_shadow_audit(
    db: Session,
    *,
    query: Query,
    user_id: str,
    candidate_answer: str,
    delivered_answer: str,
    source_snapshot: Sequence[Mapping[str, Any]],
    claim_verifications: Any,
    output_guard_flagged: bool,
    verifier_model: str | None = None,
) -> EvidenceGateRun:
    """Create one immutable shadow-mode audit and its claim records.

    ``query`` must already be persisted so the audit foreign key has a stable identity.
    This function flushes only its new records and intentionally leaves committing or
    rolling back to its caller. A failure therefore cannot invent a successful verdict.
    """
    started = time.perf_counter()
    sources = _normalize_sources(source_snapshot)
    claims, verification_available = _normalize_claims(claim_verifications)
    gate_input = EvidenceGateInput(
        candidate_answer=candidate_answer,
        delivered_answer=delivered_answer,
        sources=sources,
        claims=claims,
        verification_available=verification_available,
        output_guard_flagged=output_guard_flagged,
        mode=EvidenceGateMode.SHADOW,
        policy_version=POLICY_VERSION,
    )
    decision = evaluate_evidence_gate(gate_input)

    run = EvidenceGateRun(
        query_id=query.id,
        user_id=user_id,
        attempt=1,
        policy_version=POLICY_VERSION,
        mode=EvidenceGateMode.SHADOW.value,
        status=decision.status.value,
        action=decision.action.value,
        candidate_answer_sha256=text_sha256(candidate_answer),
        delivered_answer_sha256=text_sha256(delivered_answer),
        source_snapshot_sha256=source_snapshot_sha256(sources),
        verifier_model=verifier_model,
        latency_ms=round((time.perf_counter() - started) * 1000),
        claim_count=len(claims),
        supported_count=decision.supported_count,
        unsupported_count=decision.unsupported_count,
        unverified_count=decision.unverified_count,
        error_code=decision.error_code,
    )
    db.add(run)
    db.flush()

    for ordinal, claim in enumerate(claims, start=1):
        db.add(
            EvidenceGateClaimModel(
                gate_run_id=run.id,
                ordinal=ordinal,
                claim_text=claim.claim,
                claim_sha256=text_sha256(claim.claim),
                verdict=claim.verdict.value,
                reason=claim.reason,
                supporting_source_numbers=list(claim.supporting_source_numbers),
            )
        )
    db.flush()
    return run


def shadow_audit_summary(run: EvidenceGateRun) -> ShadowAuditSummary:
    """Map a persisted run to the deliberately small public summary contract."""
    return ShadowAuditSummary(
        id=run.id,
        policy_version=run.policy_version,
        mode=run.mode,
        status=run.status,
        action=run.action,
        claim_count=run.claim_count,
        supported_count=run.supported_count,
        unsupported_count=run.unsupported_count,
        unverified_count=run.unverified_count,
        verified_at=run.created_at,
    )


def _normalize_sources(source_snapshot: Sequence[Mapping[str, Any]]) -> tuple[EvidenceSource, ...]:
    sources: list[EvidenceSource] = []
    for source in source_snapshot:
        if not isinstance(source, Mapping):
            raise ValueError("source snapshot entries must be mappings")
        number = source.get("source_number")
        sources.append(EvidenceSource(source_number=number, payload=dict(source)))
    return tuple(sources)


def _normalize_claims(raw_claims: Any) -> tuple[tuple[EvidenceGateClaim, ...], bool]:
    if not isinstance(raw_claims, list):
        return (), False

    claims: list[EvidenceGateClaim] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, Mapping):
            claims.append(
                EvidenceGateClaim(
                    claim="",
                    verdict=EvidenceGateVerdict.UNVERIFIED,
                    reason="Malformed claim verification result.",
                )
            )
            continue

        raw_status = raw_claim.get("status")
        try:
            verdict = EvidenceGateVerdict(raw_status)
        except ValueError:
            verdict = EvidenceGateVerdict.UNVERIFIED

        links = raw_claim.get("supporting_sources")
        if not isinstance(links, list):
            links = []
        claim_text = raw_claim.get("claim")
        claims.append(
            EvidenceGateClaim(
                claim=claim_text if isinstance(claim_text, str) else "",
                verdict=verdict,
                supporting_source_numbers=tuple(links),
                reason=raw_claim.get("reason") if isinstance(raw_claim.get("reason"), str) else None,
            )
        )
    return tuple(claims), True
