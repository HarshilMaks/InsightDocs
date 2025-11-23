.PHONY: help install install-dev test test-cov lint clean run-backend run-worker docker-up docker-down docker-logs docker-rebuild venv

SHELL := /bin/bash
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/uv pip
ACTIVATE := . $(VENV)/bin/activate

help:
	@echo "InsightDocs Development Commands"
	@echo "================================"
	@echo "venv             - Create virtual environment"
	@echo "install          - Install production dependencies"
	@echo "install-dev      - Install development dependencies"
	@echo "test             - Run tests"
	@echo "test-cov         - Run tests with coverage"
	@echo "lint             - Run code linters"
	@echo "clean            - Clean up cache and temporary files"
	@echo "run-backend      - Run the API server"
	@echo "run-worker       - Run Celery worker"
	@echo "docker-up        - Start all services with Docker Compose"
	@echo "docker-down      - Stop all services"
	@echo "docker-logs      - View Docker logs"
	@echo "docker-rebuild   - Rebuild and restart Docker services"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
		$(PIP) install --upgrade pip; \
		echo "Virtual environment created at $(VENV)"; \
	else \
		echo "Virtual environment already exists at $(VENV)"; \
	fi

install:
	@if [ ! -d "$(VENV)" ]; then echo "Error: Virtual environment not found. Run 'make venv' first."; exit 1; fi
	$(ACTIVATE) && uv pip install -r requirements.txt

install-dev:
	@if [ ! -d "$(VENV)" ]; then echo "Error: Virtual environment not found. Run 'make venv' first."; exit 1; fi
	$(ACTIVATE) && uv pip install -r requirements.txt
	@if [ -f requirements-dev.txt ]; then \
		$(ACTIVATE) && uv pip install -r requirements-dev.txt; \
	else \
		echo "Note: requirements-dev.txt not found, skipping dev dependencies"; \
	fi

test:
	@if [ ! -d "$(VENV)" ]; then echo "Error: Virtual environment not found. Run 'make venv' first."; exit 1; fi
	$(ACTIVATE) && pytest tests/ -v

test-cov:
	@if [ ! -d "$(VENV)" ]; then echo "Error: Virtual environment not found. Run 'make venv' first."; exit 1; fi
	$(ACTIVATE) && pytest tests/ --cov=backend --cov-report=html --cov-report=term

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
	@if [ ! -d "$(VENV)" ]; then echo "Error: Virtual environment not found. Run 'make venv' first."; exit 1; fi
	$(ACTIVATE) && uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	@if [ ! -d "$(VENV)" ]; then echo "Error: Virtual environment not found. Run 'make venv' first."; exit 1; fi
	$(ACTIVATE) && celery -A backend.workers.celery_app worker --loglevel=info

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
