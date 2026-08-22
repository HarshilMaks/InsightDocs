"""Deterministic policy semantics for Evidence Gate v1.

This module classifies supplied claim-verification results; it does not invoke an LLM,
retrieve sources, mutate a response, or persist data. That separation keeps the first
phase safe to test and lets later adapters use exactly the same policy.
"""
from __future__ import annotations

from .contracts import (
    EvidenceGateAction,
    EvidenceGateDecision,
    EvidenceGateInput,
    EvidenceGateMode,
    EvidenceGateStatus,
    EvidenceGateVerdict,
)


def evaluate_evidence_gate(gate_input: EvidenceGateInput) -> EvidenceGateDecision:
    """Resolve a gate decision without changing answer delivery.

    A decision is deliberately conservative: missing verification, malformed source
    links, source-less analyses, and unverified claims are degraded rather than passed.
    Output-guard substitutions are abstentions, never successful evidence assessments.
    """
    counts = _claim_counts(gate_input)

    if gate_input.output_guard_flagged or gate_input.candidate_answer != gate_input.delivered_answer:
        return _decision(
            status=EvidenceGateStatus.ABSTAINED,
            mode=gate_input.mode,
            error_code="DELIVERED_ANSWER_DIFFERS_FROM_CANDIDATE",
            **counts,
        )

    if not gate_input.verification_available:
        return _decision(
            status=EvidenceGateStatus.DEGRADED,
            mode=gate_input.mode,
            error_code="VERIFICATION_UNAVAILABLE",
            **counts,
        )

    source_error = _source_link_error(gate_input)
    if source_error:
        return _decision(
            status=EvidenceGateStatus.DEGRADED,
            mode=gate_input.mode,
            error_code=source_error,
            **counts,
        )

    if not gate_input.claims:
        return _decision(
            status=EvidenceGateStatus.DEGRADED,
            mode=gate_input.mode,
            error_code="NO_VERIFIABLE_CLAIMS",
            **counts,
        )

    if counts["unverified_count"]:
        return _decision(
            status=EvidenceGateStatus.DEGRADED,
            mode=gate_input.mode,
            error_code="UNVERIFIED_CLAIMS_PRESENT",
            **counts,
        )

    if counts["unsupported_count"]:
        return _decision(
            status=EvidenceGateStatus.FAILED,
            mode=gate_input.mode,
            error_code=None,
            **counts,
        )

    return _decision(
        status=EvidenceGateStatus.PASSED,
        mode=gate_input.mode,
        error_code=None,
        **counts,
    )


def _claim_counts(gate_input: EvidenceGateInput) -> dict[str, int]:
    return {
        "supported_count": sum(
            claim.verdict == EvidenceGateVerdict.SUPPORTED for claim in gate_input.claims
        ),
        "unsupported_count": sum(
            claim.verdict == EvidenceGateVerdict.UNSUPPORTED for claim in gate_input.claims
        ),
        "unverified_count": sum(
            claim.verdict == EvidenceGateVerdict.UNVERIFIED for claim in gate_input.claims
        ),
    }


def _source_link_error(gate_input: EvidenceGateInput) -> str | None:
    source_numbers: set[int] = set()
    for source in gate_input.sources:
        if isinstance(source.source_number, bool) or not isinstance(source.source_number, int):
            return "INVALID_SOURCE_NUMBER"
        if source.source_number <= 0:
            return "INVALID_SOURCE_NUMBER"
        if source.source_number in source_numbers:
            return "DUPLICATE_SOURCE_NUMBER"
        source_numbers.add(source.source_number)

    if not source_numbers:
        return "NO_RESOLVABLE_SOURCES"

    for claim in gate_input.claims:
        links = claim.supporting_source_numbers
        if claim.verdict == EvidenceGateVerdict.SUPPORTED and not links:
            return "SUPPORTED_CLAIM_MISSING_SOURCE_LINK"
        if len(set(links)) != len(links):
            return "DUPLICATE_CLAIM_SOURCE_LINK"
        for source_number in links:
            if isinstance(source_number, bool) or not isinstance(source_number, int) or source_number <= 0:
                return "INVALID_CLAIM_SOURCE_LINK"
            if source_number not in source_numbers:
                return "UNKNOWN_CLAIM_SOURCE_LINK"
    return None


def _decision(
    *,
    status: EvidenceGateStatus,
    mode: EvidenceGateMode,
    error_code: str | None,
    supported_count: int,
    unsupported_count: int,
    unverified_count: int,
) -> EvidenceGateDecision:
    if status == EvidenceGateStatus.PASSED:
        action = EvidenceGateAction.ALLOW
    elif status == EvidenceGateStatus.ABSTAINED:
        action = EvidenceGateAction.ABSTAIN
    elif mode == EvidenceGateMode.SHADOW:
        action = EvidenceGateAction.ALLOW
    elif mode == EvidenceGateMode.ANNOTATE:
        action = EvidenceGateAction.ANNOTATE
    else:
        action = EvidenceGateAction.ABSTAIN

    return EvidenceGateDecision(
        status=status,
        action=action,
        error_code=error_code,
        supported_count=supported_count,
        unsupported_count=unsupported_count,
        unverified_count=unverified_count,
    )
