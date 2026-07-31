"""Tests for per-claim verification (Roadmap Phase 3, Milestone 3).

Covers the acceptance criteria: a claim unsupported by context is flagged
individually (not just the whole answer), a fully supported answer's
claims are marked supported, and verification failures fail open rather
than breaking the query.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.middleware.guardrails import verify_claims


def _mock_gemini_response(payload: dict):
    response = MagicMock()
    response.text = json.dumps(payload)
    return response


class TestVerifyClaims:
    def test_no_answer_or_no_context_returns_none_without_calling_gemini(self):
        with patch("backend.middleware.guardrails._get_gemini_client") as mock_get_client:
            assert verify_claims("", [{"text": "x", "citation": {"source_number": 1}}]) is None
            assert verify_claims("An answer", []) is None
        mock_get_client.assert_not_called()

    def test_supported_and_unsupported_claims_are_classified_individually(self):
        context = [
            {"text": "Gemini 2.5 Flash is the default model.", "citation": {"source_number": 1}},
            {"text": "The system uses PostgreSQL for metadata.", "citation": {"source_number": 2}},
        ]
        answer = "Gemini 2.5 Flash is the default model. The system uses MongoDB for storage."

        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response({
            "claims": [
                {
                    "claim": "Gemini 2.5 Flash is the default model.",
                    "status": "supported",
                    "supporting_sources": [1],
                    "reason": None,
                },
                {
                    "claim": "The system uses MongoDB for storage.",
                    "status": "unsupported",
                    "supporting_sources": [],
                    "reason": "The sources mention PostgreSQL, not MongoDB.",
                },
            ]
        })

        with patch("backend.middleware.guardrails._get_gemini_client", return_value=mock_model), patch(
            "backend.middleware.guardrails.genai"
        ):
            results = verify_claims(answer, context, api_key="AIzaSy_test_key")

        assert results is not None
        assert len(results) == 2

        supported = next(r for r in results if r["claim"].startswith("Gemini"))
        unsupported = next(r for r in results if r["claim"].startswith("The system"))

        assert supported["status"] == "supported"
        assert supported["supporting_sources"] == [1]
        assert supported["reason"] is None

        assert unsupported["status"] == "unsupported"
        assert unsupported["supporting_sources"] == []
        assert "PostgreSQL" in unsupported["reason"]

    def test_no_gemini_client_fails_open_returns_none(self):
        with patch("backend.middleware.guardrails._get_gemini_client", return_value=None):
            result = verify_claims(
                "Some answer.",
                [{"text": "context", "citation": {"source_number": 1}}],
            )
        assert result is None

    def test_malformed_json_response_fails_open_returns_none(self):
        mock_model = MagicMock()
        response = MagicMock()
        response.text = "this is not json"
        mock_model.generate_content.return_value = response

        with patch("backend.middleware.guardrails._get_gemini_client", return_value=mock_model), patch(
            "backend.middleware.guardrails.genai"
        ):
            result = verify_claims(
                "Some answer.",
                [{"text": "context", "citation": {"source_number": 1}}],
            )
        assert result is None

    def test_gemini_call_exception_fails_open_returns_none(self):
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("network error")

        with patch("backend.middleware.guardrails._get_gemini_client", return_value=mock_model), patch(
            "backend.middleware.guardrails.genai"
        ):
            result = verify_claims(
                "Some answer.",
                [{"text": "context", "citation": {"source_number": 1}}],
            )
        assert result is None

    def test_response_with_no_verifiable_claims_returns_empty_list(self):
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response({"claims": []})

        with patch("backend.middleware.guardrails._get_gemini_client", return_value=mock_model), patch(
            "backend.middleware.guardrails.genai"
        ):
            result = verify_claims(
                "Could you clarify your question?",
                [{"text": "context", "citation": {"source_number": 1}}],
            )
        assert result == []

    def test_unknown_status_value_defaults_to_unsupported(self):
        """A malformed status from the model must not silently become
        'supported' — default to the more conservative classification."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response({
            "claims": [
                {"claim": "Some claim.", "status": "maybe", "supporting_sources": []}
            ]
        })

        with patch("backend.middleware.guardrails._get_gemini_client", return_value=mock_model), patch(
            "backend.middleware.guardrails.genai"
        ):
            result = verify_claims(
                "Some claim.",
                [{"text": "context", "citation": {"source_number": 1}}],
            )
        assert result[0]["status"] == "unsupported"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
