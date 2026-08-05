#!/usr/bin/env bash
# Start script for Celery worker service
set -o errexit

echo "=== Starting Celery Worker ==="
celery -A backend.workers.celery_app worker --loglevel=info --concurrency=2
