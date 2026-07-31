#!/usr/bin/env bash
# Start script for Render FastAPI API service
set -o errexit

echo "=== Running database migrations ==="
# Run Alembic migrations to make sure schema is up to date
alembic upgrade head || echo "Database migration failed or skipped (verify DATABASE_URL)."

echo "=== Starting FastAPI Application ==="
uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-10000}
