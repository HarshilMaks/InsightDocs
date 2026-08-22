import pytest

from backend.evidence_gate import (
    EvidenceGateAction,
    EvidenceGateClaim,
    EvidenceGateInput,
    EvidenceGateMode,
    EvidenceGateStatus,
    EvidenceGateVerdict,
    EvidenceSource,
    evaluate_evidence_gate,
    source_snapshot_sha256,
    text_sha256,
)


def _source(number: int = 1) -> EvidenceSource:
    return EvidenceSource(
        source_number=number,
        payload={"document_id": "doc-1", "page_number": 2, "content": "PostgreSQL stores metadata."},
    )


def _claim(
    verdict: EvidenceGateVerdict = EvidenceGateVerdict.SUPPORTED,
    links: tuple[int, ...] = (1,),
) -> EvidenceGateClaim:
    return EvidenceGateClaim(
        claim="PostgreSQL stores metadata.",
        verdict=verdict,
        supporting_source_numbers=links,
    )


def _input(**overrides) -> EvidenceGateInput:
    values = {
        "candidate_answer": "PostgreSQL stores metadata.",
        "delivered_answer": "PostgreSQL stores metadata.",
        "sources": (_source(),),
        "claims": (_claim(),),
        "verification_available": True,
    }
    values.update(overrides)
    return EvidenceGateInput(**values)


def test_supported_claims_pass_and_allow():
    decision = evaluate_evidence_gate(_input())

    assert decision.status == EvidenceGateStatus.PASSED
    assert decision.action == EvidenceGateAction.ALLOW
    assert decision.error_code is None
    assert (decision.supported_count, decision.unsupported_count, decision.unverified_count) == (1, 0, 0)


@pytest.mark.parametrize(
    ("mode", "expected_action"),
    [
        (EvidenceGateMode.SHADOW, EvidenceGateAction.ALLOW),
        (EvidenceGateMode.ANNOTATE, EvidenceGateAction.ANNOTATE),
        (EvidenceGateMode.ENFORCE, EvidenceGateAction.ABSTAIN),
    ],
)
def test_unsupported_claims_follow_mode_without_changing_status(mode, expected_action):
    decision = evaluate_evidence_gate(
        _input(mode=mode, claims=(_claim(EvidenceGateVerdict.UNSUPPORTED),))
    )

    assert decision.status == EvidenceGateStatus.FAILED
    assert decision.action == expected_action
    assert decision.unsupported_count == 1


def test_unavailable_verification_is_degraded_not_passed():
    decision = evaluate_evidence_gate(_input(verification_available=False))

    assert decision.status == EvidenceGateStatus.DEGRADED
    assert decision.action == EvidenceGateAction.ALLOW
    assert decision.error_code == "VERIFICATION_UNAVAILABLE"


@pytest.mark.parametrize(
    ("claims", "sources", "error_code"),
    [
        ((_claim(links=()),), (_source(),), "SUPPORTED_CLAIM_MISSING_SOURCE_LINK"),
        ((_claim(links=(2,)),), (_source(),), "UNKNOWN_CLAIM_SOURCE_LINK"),
        ((_claim(links=(1, 1)),), (_source(),), "DUPLICATE_CLAIM_SOURCE_LINK"),
        ((_claim(),), (), "NO_RESOLVABLE_SOURCES"),
        ((_claim(),), (_source(0),), "INVALID_SOURCE_NUMBER"),
    ],
)
def test_invalid_source_links_degrade_the_run(claims, sources, error_code):
    decision = evaluate_evidence_gate(_input(claims=claims, sources=sources))

    assert decision.status == EvidenceGateStatus.DEGRADED
    assert decision.error_code == error_code


def test_unverified_or_empty_claims_degrade_the_run():
    unverified = evaluate_evidence_gate(
        _input(claims=(_claim(EvidenceGateVerdict.UNVERIFIED),))
    )
    empty = evaluate_evidence_gate(_input(claims=()))

    assert (unverified.status, unverified.error_code) == (
        EvidenceGateStatus.DEGRADED,
        "UNVERIFIED_CLAIMS_PRESENT",
    )
    assert (empty.status, empty.error_code) == (
        EvidenceGateStatus.DEGRADED,
        "NO_VERIFIABLE_CLAIMS",
    )


def test_guard_substitution_is_abstained_and_never_passed():
    decision = evaluate_evidence_gate(
        _input(
            delivered_answer="I cannot provide a response from the supplied evidence.",
            output_guard_flagged=True,
        )
    )

    assert decision.status == EvidenceGateStatus.ABSTAINED
    assert decision.action == EvidenceGateAction.ABSTAIN
    assert decision.error_code == "DELIVERED_ANSWER_DIFFERS_FROM_CANDIDATE"


def test_hashes_are_stable_for_equivalent_text_and_mapping_order():
    assert text_sha256("A\r\nB") == text_sha256("Ａ   B")

    first = (EvidenceSource(1, {"b": 2, "a": 1}),)
    second = (EvidenceSource(1, {"a": 1, "b": 2}),)
    assert source_snapshot_sha256(first) == source_snapshot_sha256(second)


def test_source_snapshot_rejects_non_json_payload():
    with pytest.raises(ValueError, match="JSON serializable"):
        source_snapshot_sha256((EvidenceSource(1, {"bad": object()}),))
