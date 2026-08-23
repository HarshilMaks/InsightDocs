"""Tests for per-claim verification through the shared Gemini fallback path."""
import json
from unittest.mock import patch

from backend.middleware.guardrails import verify_claims


def _claim_payload(claims: list[dict]) -> str:
    return json.dumps({"claims": claims})


class TestVerifyClaims:
    def test_no_answer_or_no_context_returns_none_without_generation(self):
        with patch("backend.middleware.guardrails._generate_guardrail_text") as generate:
            assert verify_claims("", [{"text": "x", "citation": {"source_number": 1}}]) is None
            assert verify_claims("An answer", []) is None
        generate.assert_not_called()

    def test_supported_and_unsupported_claims_are_classified_individually(self):
        context = [
            {"text": "The system uses PostgreSQL for metadata.", "citation": {"source_number": 1}},
            {"text": "Milvus stores vectors.", "citation": {"source_number": 2}},
        ]
        answer = "The system uses PostgreSQL for metadata. It uses MongoDB for storage."
        generated = _claim_payload([
            {
                "claim": "The system uses PostgreSQL for metadata.",
                "status": "supported",
                "supporting_sources": [1],
            },
            {
                "claim": "It uses MongoDB for storage.",
                "status": "unsupported",
                "supporting_sources": [],
                "reason": "The sources mention PostgreSQL, not MongoDB.",
            },
        ])

        with patch("backend.middleware.guardrails._generate_guardrail_text", return_value=generated) as generate:
            results = verify_claims(answer, context, api_key="AIzaSy_test_key")

        assert results is not None
        assert len(results) == 2
        assert results[0]["status"] == "supported"
        assert results[0]["supporting_sources"] == [1]
        assert results[1]["status"] == "unsupported"
        assert "PostgreSQL" in results[1]["reason"]
        assert generate.call_args.kwargs == {"api_key": "AIzaSy_test_key", "max_output_tokens": 1024}

    def test_generation_failure_fails_open_returns_none(self):
        with patch(
            "backend.middleware.guardrails._generate_guardrail_text",
            side_effect=RuntimeError("network error"),
        ):
            result = verify_claims("Some answer.", [{"text": "context", "citation": {"source_number": 1}}])
        assert result is None

    def test_malformed_json_fails_open_returns_none(self):
        with patch("backend.middleware.guardrails._generate_guardrail_text", return_value="not json"):
            result = verify_claims("Some answer.", [{"text": "context", "citation": {"source_number": 1}}])
        assert result is None

    def test_response_with_no_verifiable_claims_returns_empty_list(self):
        with patch("backend.middleware.guardrails._generate_guardrail_text", return_value=_claim_payload([])):
            result = verify_claims(
                "Could you clarify your question?",
                [{"text": "context", "citation": {"source_number": 1}}],
            )
        assert result == []

    def test_unknown_status_value_defaults_to_unsupported(self):
        generated = _claim_payload([{"claim": "Some claim.", "status": "maybe", "supporting_sources": []}])
        with patch("backend.middleware.guardrails._generate_guardrail_text", return_value=generated):
            result = verify_claims("Some claim.", [{"text": "context", "citation": {"source_number": 1}}])
        assert result[0]["status"] == "unsupported"
