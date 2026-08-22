"""Versioned, test-only Evidence Gate fixture contract.

Fixtures describe expected claim support and visual source evidence without relying on
production UUIDs, services, or user data. They are internal pytest inputs, not a public
CLI or upload format.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from .contracts import EvidenceGateVerdict
from .hashing import text_sha256


FIXTURE_SCHEMA_VERSION = 1
COORDINATE_SPACE = "pdf_points_top_left_v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FixtureValidationError(ValueError):
    """Raised when a checked-in Evidence Gate fixture is malformed or inconsistent."""


@dataclass(frozen=True)
class ExpectedBoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class ExpectedEvidence:
    id: str
    document_logical_id: str
    page_number: int
    page_width: float
    page_height: float
    bbox: ExpectedBoundingBox
    text_exact: str
    text_sha256: str
    required_source_fields: tuple[str, ...]


@dataclass(frozen=True)
class ExpectedClaim:
    id: str
    text_contains: tuple[str, ...]
    verification: EvidenceGateVerdict
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceFixture:
    fixture_id: str
    description: str
    query: str
    document_logical_id: str
    document_filename: str
    document_sha256: str
    page_count: int
    claims: tuple[ExpectedClaim, ...]
    evidence: tuple[ExpectedEvidence, ...]


def load_evidence_fixture(path: str | Path) -> EvidenceFixture:
    """Load and validate one fixture JSON file from the repository."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureValidationError(f"unable to load fixture: {exc}") from exc
    return parse_evidence_fixture(payload)


def parse_evidence_fixture(payload: Mapping[str, Any]) -> EvidenceFixture:
    """Validate a v1 fixture and return immutable normalized contract types."""
    _require_mapping(payload, "fixture")
    if payload.get("schema_version") != FIXTURE_SCHEMA_VERSION:
        raise FixtureValidationError(
            f"schema_version must be exactly {FIXTURE_SCHEMA_VERSION}"
        )

    fixture_id = _nonempty_string(payload.get("fixture_id"), "fixture_id")
    description = _nonempty_string(payload.get("description"), "description")
    request = _mapping(payload.get("request"), "request")
    query = _nonempty_string(request.get("query"), "request.query")
    document_scope = _list(request.get("document_scope"), "request.document_scope")

    document = _mapping(payload.get("document"), "document")
    document_id = _nonempty_string(document.get("logical_id"), "document.logical_id")
    document_filename = _nonempty_string(document.get("filename"), "document.filename")
    document_sha256 = _sha256(document.get("sha256"), "document.sha256")
    page_count = _positive_int(document.get("page_count"), "document.page_count")
    if document_scope != [document_id]:
        raise FixtureValidationError("request.document_scope must contain exactly document.logical_id")

    expected = _mapping(payload.get("expected"), "expected")
    evidence = tuple(
        _parse_evidence(item, document_id, page_count, index)
        for index, item in enumerate(_list(expected.get("evidence"), "expected.evidence"))
    )
    if not evidence:
        raise FixtureValidationError("expected.evidence must not be empty")
    _ensure_unique((item.id for item in evidence), "expected.evidence IDs")

    evidence_ids = {item.id for item in evidence}
    claims = tuple(
        _parse_claim(item, evidence_ids, index)
        for index, item in enumerate(_list(expected.get("claims"), "expected.claims"))
    )
    if not claims:
        raise FixtureValidationError("expected.claims must not be empty")
    _ensure_unique((item.id for item in claims), "expected.claims IDs")

    return EvidenceFixture(
        fixture_id=fixture_id,
        description=description,
        query=query,
        document_logical_id=document_id,
        document_filename=document_filename,
        document_sha256=document_sha256,
        page_count=page_count,
        claims=claims,
        evidence=evidence,
    )


def _parse_evidence(
    value: Any, document_id: str, page_count: int, index: int
) -> ExpectedEvidence:
    path = f"expected.evidence[{index}]"
    item = _mapping(value, path)
    evidence_id = _nonempty_string(item.get("id"), f"{path}.id")
    if _nonempty_string(item.get("document_logical_id"), f"{path}.document_logical_id") != document_id:
        raise FixtureValidationError(f"{path}.document_logical_id must match document.logical_id")
    page_number = _positive_int(item.get("page_number"), f"{path}.page_number")
    if page_number > page_count:
        raise FixtureValidationError(f"{path}.page_number must be within document.page_count")
    if item.get("coordinate_space") != COORDINATE_SPACE:
        raise FixtureValidationError(f"{path}.coordinate_space must be {COORDINATE_SPACE}")

    size = _mapping(item.get("page_size_points"), f"{path}.page_size_points")
    width = _positive_number(size.get("width"), f"{path}.page_size_points.width")
    height = _positive_number(size.get("height"), f"{path}.page_size_points.height")
    raw_bbox = _mapping(item.get("bbox"), f"{path}.bbox")
    bbox = ExpectedBoundingBox(
        x1=_finite_number(raw_bbox.get("x1"), f"{path}.bbox.x1"),
        y1=_finite_number(raw_bbox.get("y1"), f"{path}.bbox.y1"),
        x2=_finite_number(raw_bbox.get("x2"), f"{path}.bbox.x2"),
        y2=_finite_number(raw_bbox.get("y2"), f"{path}.bbox.y2"),
    )
    if not (0 <= bbox.x1 < bbox.x2 <= width and 0 <= bbox.y1 < bbox.y2 <= height):
        raise FixtureValidationError(f"{path}.bbox must be inside page_size_points")

    text_exact = _nonempty_string(item.get("text_exact"), f"{path}.text_exact")
    expected_hash = _sha256(item.get("text_sha256"), f"{path}.text_sha256")
    if expected_hash != text_sha256(text_exact):
        raise FixtureValidationError(f"{path}.text_sha256 does not match normalized text_exact")

    raw_required = _list(item.get("required_source_fields"), f"{path}.required_source_fields")
    required = tuple(_nonempty_string(field, f"{path}.required_source_fields") for field in raw_required)
    if not required:
        raise FixtureValidationError(f"{path}.required_source_fields must not be empty")
    _ensure_unique(required, f"{path}.required_source_fields")

    return ExpectedEvidence(
        id=evidence_id,
        document_logical_id=document_id,
        page_number=page_number,
        page_width=width,
        page_height=height,
        bbox=bbox,
        text_exact=text_exact,
        text_sha256=expected_hash,
        required_source_fields=required,
    )


def _parse_claim(value: Any, evidence_ids: set[str], index: int) -> ExpectedClaim:
    path = f"expected.claims[{index}]"
    item = _mapping(value, path)
    claim_id = _nonempty_string(item.get("id"), f"{path}.id")
    tokens = tuple(
        _nonempty_string(token, f"{path}.text_contains")
        for token in _list(item.get("text_contains"), f"{path}.text_contains")
    )
    if not tokens:
        raise FixtureValidationError(f"{path}.text_contains must not be empty")
    try:
        verification = EvidenceGateVerdict(item.get("verification"))
    except ValueError as exc:
        raise FixtureValidationError(f"{path}.verification is invalid") from exc

    refs = tuple(
        _nonempty_string(reference, f"{path}.evidence_refs")
        for reference in _list(item.get("evidence_refs"), f"{path}.evidence_refs")
    )
    if verification == EvidenceGateVerdict.SUPPORTED and not refs:
        raise FixtureValidationError(f"{path}.evidence_refs is required for supported claims")
    if any(reference not in evidence_ids for reference in refs):
        raise FixtureValidationError(f"{path}.evidence_refs contains an unknown evidence ID")
    _ensure_unique(refs, f"{path}.evidence_refs")

    return ExpectedClaim(
        id=claim_id,
        text_contains=tokens,
        verification=verification,
        evidence_refs=refs,
    )


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FixtureValidationError(f"{path} must be an object")
    return value


def _require_mapping(value: Any, path: str) -> None:
    _mapping(value, path)


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise FixtureValidationError(f"{path} must be an array")
    return value


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FixtureValidationError(f"{path} must be a non-empty string")
    return value.strip()


def _sha256(value: Any, path: str) -> str:
    value = _nonempty_string(value, path)
    if not _SHA256_RE.fullmatch(value):
        raise FixtureValidationError(f"{path} must be a lowercase SHA-256 hex digest")
    return value


def _positive_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FixtureValidationError(f"{path} must be a positive integer")
    return value


def _finite_number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise FixtureValidationError(f"{path} must be a finite number")
    return float(value)


def _positive_number(value: Any, path: str) -> float:
    number = _finite_number(value, path)
    if number <= 0:
        raise FixtureValidationError(f"{path} must be greater than zero")
    return number


def _ensure_unique(values: Sequence[str] | Any, path: str) -> None:
    items = list(values)
    if len(items) != len(set(items)):
        raise FixtureValidationError(f"{path} must be unique")
