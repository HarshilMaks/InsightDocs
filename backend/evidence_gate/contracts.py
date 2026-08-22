"""Pure contracts for the additive Evidence Gate domain.

These types deliberately have no FastAPI, SQLAlchemy, LLM, or worker dependency so
policy evaluation is deterministic and can later be reused by local tooling.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class EvidenceGateMode(str, Enum):
    """How a gate decision affects answer delivery."""

    SHADOW = "shadow"
    ANNOTATE = "annotate"
    ENFORCE = "enforce"


class EvidenceGateStatus(str, Enum):
    """Assessment result, distinct from the delivery action."""

    PASSED = "passed"
    FAILED = "failed"
    DEGRADED = "degraded"
    ABSTAINED = "abstained"


class EvidenceGateAction(str, Enum):
    """Action taken after assessment."""

    ALLOW = "allow"
    ANNOTATE = "annotate"
    ABSTAIN = "abstain"


class EvidenceGateVerdict(str, Enum):
    """Per-claim evidence assessment."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class EvidenceSource:
    """A source entry from the immutable request-time retrieval snapshot."""

    source_number: int
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class EvidenceGateClaim:
    """A normalized candidate-answer claim and its source-number links."""

    claim: str
    verdict: EvidenceGateVerdict
    supporting_source_numbers: tuple[int, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class EvidenceGateInput:
    """Server-owned, normalized input required for one policy assessment."""

    candidate_answer: str
    delivered_answer: str
    sources: tuple[EvidenceSource, ...]
    claims: tuple[EvidenceGateClaim, ...]
    verification_available: bool
    output_guard_flagged: bool = False
    mode: EvidenceGateMode = EvidenceGateMode.SHADOW
    policy_version: str = "evidence-gate/v1"


@dataclass(frozen=True)
class EvidenceGateDecision:
    """Deterministic policy output suitable for persistence or reporting."""

    status: EvidenceGateStatus
    action: EvidenceGateAction
    error_code: str | None
    supported_count: int
    unsupported_count: int
    unverified_count: int
