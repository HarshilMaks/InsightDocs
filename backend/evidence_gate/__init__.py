"""Additive Evidence Gate domain package.

Phase 1 exposes only pure contract, hashing, and policy primitives. Live query wiring,
workers, HTTP endpoints, and reviewer UI are intentionally deferred.
"""
from .contracts import (
    EvidenceGateAction,
    EvidenceGateClaim,
    EvidenceGateDecision,
    EvidenceGateInput,
    EvidenceGateMode,
    EvidenceGateStatus,
    EvidenceGateVerdict,
    EvidenceSource,
)
from .fixture_contract import (
    EvidenceFixture,
    FixtureValidationError,
    load_evidence_fixture,
    parse_evidence_fixture,
)
from .hashing import source_snapshot_sha256, text_sha256
from .policy import evaluate_evidence_gate
from .regression import (
    RegressionFinding,
    RegressionMetrics,
    RegressionResult,
    evaluate_evidence_fixture,
)

__all__ = [
    "EvidenceGateAction",
    "EvidenceGateClaim",
    "EvidenceGateDecision",
    "EvidenceGateInput",
    "EvidenceGateMode",
    "EvidenceGateStatus",
    "EvidenceGateVerdict",
    "EvidenceSource",
    "EvidenceFixture",
    "FixtureValidationError",
    "RegressionFinding",
    "RegressionMetrics",
    "RegressionResult",
    "evaluate_evidence_fixture",
    "evaluate_evidence_gate",
    "load_evidence_fixture",
    "parse_evidence_fixture",
    "source_snapshot_sha256",
    "text_sha256",
]
