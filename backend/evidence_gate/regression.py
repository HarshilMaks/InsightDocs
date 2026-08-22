"""Internal, deterministic Evidence Gate regression evaluation.

This is a backend/testing helper. It accepts in-memory normalized response mappings and
returns structured findings for pytest and future server-side quality workflows. It has
no CLI, HTTP, database, or LLM dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .fixture_contract import EvidenceFixture, ExpectedEvidence
from .hashing import normalize_text


DEFAULT_BBOX_TOLERANCE_POINTS = 0.5


@dataclass(frozen=True)
class RegressionFinding:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class RegressionMetrics:
    expected_claims: int
    claims_matched: int
    verdicts_matched: int
    expected_evidence: int
    evidence_matched: int
    required_fields_matched: int
    pages_matched: int
    bboxes_matched: int
    text_matches: int


@dataclass(frozen=True)
class RegressionResult:
    passed: bool
    findings: tuple[RegressionFinding, ...]
    metrics: RegressionMetrics


def evaluate_evidence_fixture(
    fixture: EvidenceFixture,
    response: Mapping[str, Any],
    *,
    bbox_tolerance_points: float = DEFAULT_BBOX_TOLERANCE_POINTS,
) -> RegressionResult:
    """Compare a normalized response with one expected evidence fixture.

    The caller provides the response dictionary in the same shape as InsightDocs query
    responses: ``sources`` and ``claim_verifications``. Missing/malformed response
    fields produce deterministic findings instead of exceptions.
    """
    if bbox_tolerance_points < 0:
        raise ValueError("bbox_tolerance_points must be non-negative")

    findings: list[RegressionFinding] = []
    source_by_number = _sources_by_number(response.get("sources"), findings)
    actual_claims = _claim_mappings(response.get("claim_verifications"), findings)

    claims_matched = 0
    verdicts_matched = 0
    evidence_matched = 0
    required_fields_matched = 0
    pages_matched = 0
    bboxes_matched = 0
    text_matches = 0

    evidence_by_id = {evidence.id: evidence for evidence in fixture.evidence}

    for expected_claim in fixture.claims:
        actual_claim = _find_claim(expected_claim.text_contains, actual_claims)
        claim_path = f"claims.{expected_claim.id}"
        if actual_claim is None:
            findings.append(
                RegressionFinding(
                    "CLAIM_MISSING", claim_path,
                    "No response claim contains every required expected token.",
                )
            )
            continue
        claims_matched += 1

        if actual_claim.get("status") != expected_claim.verification.value:
            findings.append(
                RegressionFinding(
                    "CLAIM_VERDICT_MISMATCH", claim_path,
                    f"Expected {expected_claim.verification.value!r}, got {actual_claim.get('status')!r}.",
                )
            )
        else:
            verdicts_matched += 1

        links = actual_claim.get("supporting_sources")
        if not isinstance(links, list):
            findings.append(
                RegressionFinding("CLAIM_SOURCE_LINKS_INVALID", claim_path, "supporting_sources must be an array.")
            )
            continue

        for evidence_id in expected_claim.evidence_refs:
            evidence = evidence_by_id[evidence_id]
            matching_source_number = _find_matching_source_number(links, source_by_number, evidence)
            evidence_path = f"{claim_path}.evidence.{evidence_id}"
            if matching_source_number is None:
                findings.append(
                    RegressionFinding(
                        "EVIDENCE_LINK_MISSING", evidence_path,
                        "No linked response source resolves to the expected document evidence.",
                    )
                )
                continue

            source = source_by_number[matching_source_number]
            evidence_matched += 1

            field_match, field_findings = _required_fields_match(source, evidence, evidence_path)
            findings.extend(field_findings)
            required_fields_matched += int(field_match)

            page_match, page_finding = _page_matches(source, evidence, evidence_path)
            if page_finding:
                findings.append(page_finding)
            pages_matched += int(page_match)

            bbox_match, bbox_finding = _bbox_matches(
                source, evidence, evidence_path, bbox_tolerance_points
            )
            if bbox_finding:
                findings.append(bbox_finding)
            bboxes_matched += int(bbox_match)

            text_match, text_finding = _text_matches(source, evidence, evidence_path)
            if text_finding:
                findings.append(text_finding)
            text_matches += int(text_match)

    metrics = RegressionMetrics(
        expected_claims=len(fixture.claims),
        claims_matched=claims_matched,
        verdicts_matched=verdicts_matched,
        expected_evidence=sum(len(claim.evidence_refs) for claim in fixture.claims),
        evidence_matched=evidence_matched,
        required_fields_matched=required_fields_matched,
        pages_matched=pages_matched,
        bboxes_matched=bboxes_matched,
        text_matches=text_matches,
    )
    return RegressionResult(passed=not findings, findings=tuple(findings), metrics=metrics)


def _sources_by_number(raw_sources: Any, findings: list[RegressionFinding]) -> dict[int, Mapping[str, Any]]:
    if not isinstance(raw_sources, list):
        findings.append(RegressionFinding("SOURCES_INVALID", "sources", "sources must be an array."))
        return {}
    sources: dict[int, Mapping[str, Any]] = {}
    for index, source in enumerate(raw_sources):
        if not isinstance(source, Mapping):
            findings.append(RegressionFinding("SOURCE_INVALID", f"sources[{index}]", "source must be an object."))
            continue
        number = source.get("source_number")
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            findings.append(
                RegressionFinding("SOURCE_NUMBER_INVALID", f"sources[{index}]", "source_number must be a positive integer.")
            )
            continue
        if number in sources:
            findings.append(
                RegressionFinding("SOURCE_NUMBER_DUPLICATE", f"sources[{index}]", "source_number must be unique.")
            )
            continue
        sources[number] = source
    return sources


def _claim_mappings(raw_claims: Any, findings: list[RegressionFinding]) -> list[Mapping[str, Any]]:
    if not isinstance(raw_claims, list):
        findings.append(
            RegressionFinding("CLAIMS_INVALID", "claim_verifications", "claim_verifications must be an array.")
        )
        return []
    return [claim for claim in raw_claims if isinstance(claim, Mapping)]


def _find_claim(tokens: Sequence[str], actual_claims: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    normalized_tokens = [normalize_text(token).casefold() for token in tokens]
    for claim in actual_claims:
        text = claim.get("claim")
        if not isinstance(text, str):
            continue
        normalized_claim = normalize_text(text).casefold()
        if all(token in normalized_claim for token in normalized_tokens):
            return claim
    return None


def _find_matching_source_number(
    links: Sequence[Any], source_by_number: Mapping[int, Mapping[str, Any]], evidence: ExpectedEvidence
) -> int | None:
    for link in links:
        if isinstance(link, bool) or not isinstance(link, int):
            continue
        source = source_by_number.get(link)
        if source is not None and source.get("document_id") == evidence.document_logical_id:
            return link
    return None


def _required_fields_match(
    source: Mapping[str, Any], evidence: ExpectedEvidence, path: str
) -> tuple[bool, list[RegressionFinding]]:
    missing = [field for field in evidence.required_source_fields if source.get(field) is None]
    if not missing:
        return True, []
    return False, [
        RegressionFinding("SOURCE_FIELDS_MISSING", path, f"Missing required source fields: {', '.join(missing)}.")
    ]


def _page_matches(
    source: Mapping[str, Any], evidence: ExpectedEvidence, path: str
) -> tuple[bool, RegressionFinding | None]:
    if source.get("page_number") == evidence.page_number:
        return True, None
    return False, RegressionFinding(
        "PAGE_MISMATCH", path, f"Expected page {evidence.page_number}, got {source.get('page_number')!r}."
    )


def _bbox_matches(
    source: Mapping[str, Any],
    evidence: ExpectedEvidence,
    path: str,
    tolerance: float,
) -> tuple[bool, RegressionFinding | None]:
    bbox = source.get("bbox")
    if not isinstance(bbox, Mapping):
        return False, RegressionFinding("BBOX_MISSING", path, "Expected a bbox object.")
    deltas: dict[str, float] = {}
    for key, expected in (
        ("x1", evidence.bbox.x1),
        ("y1", evidence.bbox.y1),
        ("x2", evidence.bbox.x2),
        ("y2", evidence.bbox.y2),
    ):
        actual = bbox.get(key)
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            return False, RegressionFinding("BBOX_INVALID", path, f"bbox.{key} must be numeric.")
        deltas[key] = abs(float(actual) - expected)
    if all(delta <= tolerance for delta in deltas.values()):
        return True, None
    detail = ", ".join(f"{key}={delta:.3f}" for key, delta in deltas.items())
    return False, RegressionFinding(
        "BBOX_OUT_OF_TOLERANCE", path, f"BBox delta(s) exceed {tolerance} points: {detail}."
    )


def _text_matches(
    source: Mapping[str, Any], evidence: ExpectedEvidence, path: str
) -> tuple[bool, RegressionFinding | None]:
    value = source.get("content")
    if not isinstance(value, str):
        value = source.get("content_preview")
    if not isinstance(value, str):
        return False, RegressionFinding("EVIDENCE_TEXT_MISSING", path, "Source has no content or content_preview.")
    if normalize_text(evidence.text_exact).casefold() in normalize_text(value).casefold():
        return True, None
    return False, RegressionFinding(
        "EVIDENCE_TEXT_MISMATCH", path, "Expected evidence text is absent from the linked source content."
    )
