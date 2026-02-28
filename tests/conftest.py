"""Tests package configuration."""
import os
import pytest

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
