"""Vercel FastAPI entrypoint shim."""

from backend.api.main import app

__all__ = ["app"]
