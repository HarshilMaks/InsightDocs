#!/usr/bin/env bash
# Start script for Render — API only. Migrations are a release gate: serving
# against an unknown schema can corrupt history or make a stale deployment look healthy.
set -o errexit

echo "=== Running database migrations ==="
alembic upgrade head

echo "=== Starting FastAPI Application ==="
exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-10000} --timeout-keep-alive 120
