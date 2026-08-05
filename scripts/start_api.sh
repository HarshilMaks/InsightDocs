#!/usr/bin/env bash
# Start script for Render FastAPI API service
set -o errexit

echo "=== Running database migrations ==="
if ! alembic upgrade head; then
    echo "ERROR: Database migration failed. The API will NOT start with an outdated schema."
    echo "Verify DATABASE_URL is correct and the database is reachable."
    exit 1
fi

echo "=== Starting FastAPI Application ==="
uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-10000}
