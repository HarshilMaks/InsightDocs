import copy
import json
from pathlib import Path

import pytest

from backend.evidence_gate.fixture_contract import load_evidence_fixture
from backend.evidence_gate.regression import evaluate_evidence_fixture


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "evidence_gate"
FIXTURE = load_evidence_fixture(FIXTURE_DIR / "page_grounded_postgres_001.json")


def _response() -> dict:
    return json.loads((FIXTURE_DIR / "page_grounded_postgres_001_response.json").read_text(encoding="utf-8"))


def _codes(result) -> set[str]:
    return {finding.code for finding in result.findings}


def test_valid_page_grounded_response_passes_all_fixture_checks():
    result = evaluate_evidence_fixture(FIXTURE, _response())

    assert result.passed
    assert result.findings == ()
    assert result.metrics.expected_claims == result.metrics.claims_matched == 1
    assert result.metrics.verdicts_matched == 1
    assert result.metrics.expected_evidence == result.metrics.evidence_matched == 1
    assert result.metrics.required_fields_matched == 1
    assert result.metrics.pages_matched == 1
    assert result.metrics.bboxes_matched == 1
    assert result.metrics.text_matches == 1


def test_wrong_page_and_bbox_are_regressions_not_silent_matches():
    response = copy.deepcopy(_response())
    response["sources"][0]["page_number"] = 1
    response["sources"][0]["bbox"]["x1"] = 74.0

    result = evaluate_evidence_fixture(FIXTURE, response)

    assert not result.passed
    assert {"PAGE_MISMATCH", "BBOX_OUT_OF_TOLERANCE"} <= _codes(result)
    assert result.metrics.pages_matched == 0
    assert result.metrics.bboxes_matched == 0


def test_missing_or_unknown_source_link_is_a_regression():
    response = copy.deepcopy(_response())
    response["claim_verifications"][0]["supporting_sources"] = [99]

    result = evaluate_evidence_fixture(FIXTURE, response)

    assert not result.passed
    assert "EVIDENCE_LINK_MISSING" in _codes(result)
    assert result.metrics.evidence_matched == 0


def test_wrong_claim_verdict_and_evidence_text_are_regressions():
    response = copy.deepcopy(_response())
    response["claim_verifications"][0]["status"] = "unsupported"
    response["sources"][0]["content_preview"] = "The source has unrelated content."

    result = evaluate_evidence_fixture(FIXTURE, response)

    assert not result.passed
    assert {"CLAIM_VERDICT_MISMATCH", "EVIDENCE_TEXT_MISMATCH"} <= _codes(result)


def test_malformed_response_becomes_findings_instead_of_an_exception():
    result = evaluate_evidence_fixture(FIXTURE, {"sources": "not-a-list", "claim_verifications": None})

    assert not result.passed
    assert {"SOURCES_INVALID", "CLAIMS_INVALID", "CLAIM_MISSING"} <= _codes(result)


def test_negative_bbox_tolerance_is_rejected_as_a_caller_error():
    with pytest.raises(ValueError, match="non-negative"):
        evaluate_evidence_fixture(FIXTURE, _response(), bbox_tolerance_points=-0.1)
