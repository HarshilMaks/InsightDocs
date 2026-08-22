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
from .hashing import source_snapshot_sha256, text_sha256
from .policy import evaluate_evidence_gate

__all__ = [
    "EvidenceGateAction",
    "EvidenceGateClaim",
    "EvidenceGateDecision",
    "EvidenceGateInput",
    "EvidenceGateMode",
    "EvidenceGateStatus",
    "EvidenceGateVerdict",
    "EvidenceSource",
    "evaluate_evidence_gate",
    "source_snapshot_sha256",
    "text_sha256",
]
