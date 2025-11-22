.PHONY: help install install-dev test lint clean run-api run-worker docker-up docker-down

SHELL := /bin/bash

help:
	@echo "InsightDocs Development Commands"
	@echo "================================"
	@echo "install          - Install production dependencies"
	@echo "install-dev      - Install development dependencies"
	@echo "test             - Run tests"
	@echo "lint             - Run code linters"
	@echo "clean            - Clean up cache and temporary files"
	@echo "run-api          - Run the API server"
	@echo "run-worker       - Run Celery worker"
	@echo "docker-up        - Start all services with Docker Compose"
	@echo "docker-down      - Stop all services"
	@echo "docker-logs      - View Docker logs"

install:
	. .venv/bin/activate && uv pip install -r requirements.txt

install-dev:
	. .venv/bin/activate && uv pip install -r requirements.txt && uv pip install -r requirements-dev.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=insightdocs --cov-report=html --cov-report=term

lint:
	@echo "Linting would go here (flake8, black, mypy, etc.)"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

run-backend:
	. .venv/bin/activate && uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	. .venv/bin/activate && celery -A backend.workers.celery_app worker --loglevel=info

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
