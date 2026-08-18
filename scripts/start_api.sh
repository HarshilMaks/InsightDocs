#!/usr/bin/env bash
# Start script for Render — API only, port-first startup.
# Uvicorn binds the port immediately; alembic runs as part of app startup.
set -o errexit

echo "=== Running database migrations ==="
if ! alembic upgrade head; then
    echo "WARNING: Migration failed — starting API anyway so Render sees the port."
fi

echo "=== Starting FastAPI Application ==="
exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-10000} --timeout-keep-alive 120
