"""Tests package configuration."""
import pytest


@pytest.fixture(scope="session")
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("S3_BUCKET_NAME", "test")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
