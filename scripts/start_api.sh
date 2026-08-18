#!/usr/bin/env bash
# Start script for Render — API only.
# The Celery worker must run as a separate Background Worker service,
# or be omitted on the free tier (document processing will be unavailable
# but the API, auth, and queries against already-processed docs will work).
set -o errexit

echo "=== Running database migrations ==="
if ! alembic upgrade head; then
    echo "ERROR: Database migration failed."
    exit 1
fi

echo "=== Starting FastAPI Application ==="
exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-10000}
