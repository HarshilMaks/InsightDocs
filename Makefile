# Makefile for managing local and Docker-based development workflows.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# --- Local Development ---

.PHONY: install runbackend runfrontend lint format
install: ## Install/update dependencies for backend and frontend
	@echo "Installing backend dependencies..."
	@pip install --upgrade pip
	@pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd code/frontend && npm install
	@echo "All dependencies installed."

runbackend: ## Run backend server locally (localhost:8000)
	@echo "Starting backend server..."
	uvicorn code/backend/app/main:app --host 0.0.0.0 --port 8000 --reload --env-file .env

runfrontend: ## Run frontend server locally (localhost:3000)
	@echo "Starting frontend development server..."
	@cd code/frontend && npm start

lint: ## Lint backend Python code
	@echo "Linting backend code..."
	ruff check code/backend/app

format: ## Format backend Python code
	@echo "Formatting backend code..."
	ruff format code/backend/app

# --- Docker Workflow ---

.PHONY: docker-up docker-down docker-build docker-logs docker-clean docker-shell
docker-up: ## Build and start all services using Docker Compose
	@echo "Starting services via Docker Compose..."
	docker compose up --build -d

docker-down: ## Stop and remove Docker containers
	@echo "Stopping all services..."
	docker compose down

docker-build: ## Rebuild Docker images
	@echo "Rebuilding Docker images..."
	docker compose build --no-cache

docker-logs: ## Tail logs for all services
	@echo "Tailing logs..."
	docker compose logs -f

docker-clean: ## Remove containers, networks, and volumes
	@echo "Cleaning Docker environment..."
	docker compose down -v

docker-shell: ## Open shell in backend container
	@echo "Opening shell in backend container..."
	docker compose exec backend /bin/bash

# --- Help ---

.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'