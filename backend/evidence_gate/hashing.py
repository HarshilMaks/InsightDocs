"""Deterministic hashing helpers for Evidence Gate audit bindings."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping, Sequence

from .contracts import EvidenceSource


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Normalize text only for stable hashes, never for user-facing display."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    normalized = unicodedata.normalize("NFKC", value).replace("\r\n", "\n").replace("\r", "\n")
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def text_sha256(value: str) -> str:
    """Return the SHA-256 of normalized UTF-8 text."""
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a JSON-compatible value in a stable form for hashing.

    ``allow_nan=False`` prevents non-portable numeric representations from becoming
    part of the evidence identity.
    """
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("source snapshot must be JSON serializable") from exc
    return serialized.encode("utf-8")


def source_snapshot_payload(sources: Sequence[EvidenceSource]) -> list[Mapping[str, Any]]:
    """Return the canonical, source-number-bound representation of a snapshot."""
    return [
        {
            "source_number": source.source_number,
            "payload": dict(source.payload),
        }
        for source in sources
    ]


def source_snapshot_sha256(sources: Sequence[EvidenceSource]) -> str:
    """Hash the ordered, request-time source snapshot used by a gate run."""
    return hashlib.sha256(canonical_json_bytes(source_snapshot_payload(sources))).hexdigest()
