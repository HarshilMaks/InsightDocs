import copy
import json
from pathlib import Path

import pytest

from backend.evidence_gate.fixture_contract import (
    FixtureValidationError,
    load_evidence_fixture,
    parse_evidence_fixture,
)


FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "evidence_gate" / "page_grounded_postgres_001.json"
)


def _payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_checked_in_fixture_is_valid_and_normalizes_to_immutable_contract():
    fixture = load_evidence_fixture(FIXTURE_PATH)

    assert fixture.fixture_id == "page-grounded-postgres-001"
    assert fixture.document_logical_id == "fixture-document-001"
    assert fixture.claims[0].evidence_refs == ("evidence-postgres-page-2",)
    assert fixture.evidence[0].bbox.x1 == 72.0


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.update(schema_version=2), "schema_version"),
        (
            lambda p: p["expected"]["evidence"][0].update(text_sha256="0" * 64),
            "text_sha256 does not match",
        ),
        (
            lambda p: p["expected"]["evidence"][0].update(page_number=3),
            "within document.page_count",
        ),
        (
            lambda p: p["expected"]["evidence"][0]["bbox"].update(x2=700),
            "bbox must be inside",
        ),
        (
            lambda p: p["expected"]["claims"][0].update(evidence_refs=["unknown-evidence"]),
            "unknown evidence ID",
        ),
        (
            lambda p: p["request"].update(document_scope=[]),
            "document_scope",
        ),
    ],
)
def test_invalid_fixture_invariants_are_rejected(mutate, message):
    payload = copy.deepcopy(_payload())
    mutate(payload)

    with pytest.raises(FixtureValidationError, match=message):
        parse_evidence_fixture(payload)
