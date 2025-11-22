# InsightDocs Development Guide

## Project Overview

InsightDocs is a production-ready AI-driven agent architecture system that demonstrates modern best practices for building scalable, maintainable AI applications.

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- PostgreSQL 15 (if running locally)
- Redis 7 (if running locally)
- MinIO or S3 (if running locally)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs

# Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
make install-dev
# or: uv pip install -r requirements.txt && uv pip install -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration
```

### Running Services

#### Option 1: Docker Compose (Recommended)

```bash
# Start all services
make docker-up
# or: docker-compose up -d

# View logs
make docker-logs
# or: docker-compose logs -f

# Stop services
make docker-down
# or: docker-compose down
```

#### Option 2: Local Development

```bash
# Activate virtual environment first
source .venv/bin/activate

# Terminal 1: API Server
make run-backend
# or: uvicorn backend.api.main:app --reload

# Terminal 2: Celery Worker (new terminal, activate .venv again)
source .venv/bin/activate
make run-worker
# or: celery -A backend.workers.celery_app worker --loglevel=info

# Terminal 3: (Optional) Celery Flower for monitoring
source .venv/bin/activate
celery -A backend.workers.celery_app flower
```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code patterns
   - Add docstrings to all functions/classes
   - Update type hints

3. **Write tests**
   ```bash
   # Run tests
   make test
   
   # Run with coverage
   make test-cov
   ```

4. **Check code quality**
   ```bash
   make lint
   ```

5. **Commit and push**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

### Adding New Agents

1. Create agent class in `insightdocs/agents/`
2. Inherit from `BaseAgent`
3. Implement `async def process(self, message)` method
4. Add agent to `__init__.py`
5. Register with orchestrator if needed
6. Write tests in `tests/`

Example:
```python
from insightdocs.core import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, agent_id: str = "my_agent"):
        super().__init__(agent_id, "MyAgent")
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        return {"success": True, "agent_id": self.agent_id}
```

### Adding New API Endpoints

1. Create or modify router in `insightdocs/api/`
2. Define Pydantic schemas in `schemas.py`
3. Add dependency injection if needed
4. Document with docstrings
5. Add to main app in `main.py`
6. Write tests

Example:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/myroute", tags=["myroute"])

@router.get("/")
async def my_endpoint():
    return {"message": "Hello"}
```

### Database Migrations

When changing models:

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Code Style Guide

### Python Style

- Follow PEP 8
- Use type hints for all function parameters and returns
- Write docstrings in Google style
- Maximum line length: 100 characters
- Use `async/await` for I/O operations

### Docstring Example

```python
def my_function(param1: str, param2: int) -> Dict[str, Any]:
    """Brief description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Dictionary containing result
        
    Raises:
        ValueError: When param2 is negative
    """
    pass
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

Example:
```python
import os
from typing import Dict, Any

from fastapi import FastAPI
from sqlalchemy import Column

from backend.core import BaseAgent
from backend.models import Document
```

## Testing Guidelines

### Test Structure

```
tests/
├── test_agents/          # Agent tests
├── test_api/             # API endpoint tests
├── test_utils/           # Utility function tests
└── test_integration/     # Integration tests
```

### Writing Tests

```python
import pytest

@pytest.mark.asyncio
async def test_my_feature():
    """Test description."""
    # Arrange
    agent = MyAgent()
    
    # Act
    result = await agent.process({"task": "test"})
    
    # Assert
    assert result["success"] is True
```

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_core_agent.py

# With coverage
pytest --cov=insightdocs --cov-report=html

# Verbose
pytest -v
```

## Debugging

### API Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debugger
python -m debugpy --listen 5678 --wait-for-client -m uvicorn insightdocs.api.main:app
```

### Worker Debugging

```bash
# Single threaded for debugging
celery -A insightdocs.workers.celery_app worker --loglevel=debug --pool=solo
```

### Database Debugging

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U insightdocs -d insightdocs

# View tables
\dt

# Query
SELECT * FROM documents;
```

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# Your code here
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

### Monitoring

- Use Celery Flower: `http://localhost:5555`
- Check API metrics: `http://localhost:8000/metrics` (if implemented)
- Monitor logs: `docker-compose logs -f`

## Troubleshooting

### Common Issues

**Import errors**
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH=/path/to/InsightDocs:$PYTHONPATH
```

**Database connection errors**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Reset database
docker-compose down -v
docker-compose up -d
```

**Worker not picking up tasks**
```bash
# Check Redis connection
docker-compose logs redis

# Restart worker
docker-compose restart worker
```

**Gemini API errors**
- Verify API key in `.env`
- Check API quota/limits
- Ensure network connectivity

## Best Practices

### Security

- Never commit `.env` files
- Use environment variables for secrets
- Validate all user inputs
- Implement rate limiting in production
- Use HTTPS in production

### Performance

- Use async/await for I/O operations
- Batch database operations
- Cache frequently accessed data
- Use connection pooling
- Index database queries

### Code Quality

- Write self-documenting code
- Keep functions small and focused
- Use meaningful variable names
- Add comments for complex logic
- Write comprehensive tests

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code review process
- Branch naming conventions
- Commit message format
- Pull request template

## Support

- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share ideas
- Email: support@insightdocs.example.com
