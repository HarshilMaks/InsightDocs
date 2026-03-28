"""Tests package configuration."""
import os
import pytest
from unittest.mock import patch

# Set env vars before any backend imports
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("S3_BUCKET_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("MILVUS_URI", "http://localhost:19530")
os.environ.setdefault("MILVUS_TOKEN", "test")


@pytest.fixture(autouse=True)
def mock_byok_probe():
    fallback_models = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-pro",
    ]

    def _probe(api_key, model_candidates=None):
        if not api_key:
            return {
                "status": "missing",
                "model_status": "unavailable",
                "message": "No Gemini API key has been saved yet.",
                "active_model": None,
                "fallback_models": fallback_models,
                "available_models": [],
                "checked_at": "2026-03-28T00:00:00",
            }

        return {
            "status": "healthy",
            "model_status": "primary",
            "message": "Gemini key is valid. Using gemini-2.5-flash.",
            "active_model": "gemini-2.5-flash",
            "fallback_models": fallback_models,
            "available_models": ["gemini-2.5-flash", "gemini-2.0-flash"],
            "checked_at": "2026-03-28T00:00:00",
        }

    with patch("backend.api.users.probe_gemini_status", side_effect=_probe):
        yield
