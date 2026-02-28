# Development Guide

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- uv package manager

## Setup

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Running the Application

### Docker (Recommended)

```bash
make docker-up
# or
docker-compose up -d
```

### Local Development

```bash
# Terminal 1: Backend API
make run-backend
# or
uvicorn backend.api.main:app --reload

# Terminal 2: Celery Worker
make run-worker
```

## Project Structure

```
backend/
├── agents/          # Multi-agent system
├── api/             # FastAPI endpoints
├── core/            # Core framework
├── config/          # Configuration
├── models/          # Database models
├── utils/           # Utilities
├── workers/         # Celery workers
└── storage/         # Storage layer
```

## Development Patterns

### Adding New Agents

1. Create agent in `backend/agents/`:

```python
from backend.core.agent import BaseAgent

class MyAgent(BaseAgent):
    async def process(self, message: dict) -> dict:
        # Implementation
        return {"status": "completed"}
```

2. Register in `backend/agents/__init__.py`:

```python
from .my_agent import MyAgent
```

### Adding New Endpoints

1. Create/modify router in `backend/api/`:

```python
from fastapi import APIRouter
from backend.api.schemas import MyRequest, MyResponse

router = APIRouter()

@router.post("/my-endpoint", response_model=MyResponse)
async def my_endpoint(request: MyRequest):
    return MyResponse(result="success")
```

2. Define schemas in `backend/api/schemas.py`:

```python
from pydantic import BaseModel

class MyRequest(BaseModel):
    data: str

class MyResponse(BaseModel):
    result: str
```

3. Include in `backend/api/main.py`:

```python
from backend.api.my_router import router as my_router
app.include_router(my_router, prefix="/api")
```

### Adding LLM Features

Add method to `backend/utils/llm_client.py`:

```python
async def my_llm_feature(self, prompt: str) -> str:
    response = await self.client.generate_content_async(prompt)
    return response.text
```

## Testing

```bash
# Run all tests (13 tests currently)
pytest tests/ -v

# Run with coverage
pytest --cov=backend

# Run specific test
pytest tests/test_agents.py -v
```

## Code Style

- Follow PEP 8
- Use type hints
- Google-style docstrings
- async/await for I/O operations

### Import Order

```python
# Standard library
import os
from typing import Dict

# Third-party
from fastapi import FastAPI
import pytest

# Local
from backend.core.agent import BaseAgent
from backend.utils.llm_client import LLMClient
```

## Make Commands

```bash
make help           # Show available commands
make install        # Install production dependencies
make install-dev    # Install development dependencies
make test           # Run test suite
make test-cov       # Run tests with coverage
make clean          # Clean cache and temp files
make run-backend    # Start backend API
make run-worker     # Start Celery worker
make docker-up      # Start with Docker
make docker-down    # Stop Docker services
make docker-logs    # View Docker logs
```

## Debugging

### Enable Debug Logging

```bash
LOG_LEVEL=DEBUG make run-backend
```

### Debug Celery Worker

```bash
celery -A backend.workers.celery_app worker --pool=solo --loglevel=debug
```

### Database Access

```bash
docker-compose exec postgres psql -U insightdocs -d insightdocs
```

## Common Tasks

### View Logs

```bash
make docker-logs
# or
docker-compose logs -f api worker
```

### Reset Database

```bash
make docker-down
docker volume rm insightdocs_postgres_data
make docker-up
```

### Check Service Health

```bash
curl http://localhost:8000/health
```