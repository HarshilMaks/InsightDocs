#!/usr/bin/env bash
# Start script for Celery worker service
set -o errexit

echo "=== Starting Celery Worker ==="
# One process prevents parallel OCR/embedding jobs from competing for worker RAM.
exec celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1 --prefetch-multiplier=1
