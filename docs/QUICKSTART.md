# Quick Start Guide

## Installation

### 1. Prerequisites

Ensure you have the following installed:
- Python 3.11 or higher
- Docker and Docker Compose
- Git

### 2. Clone the Repository

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
```

### 3. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your-key-here
```

### 4. Start with Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (admin/minioadmin)

### 5. Alternative: Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL, Redis, and MinIO separately
# Configure .env with correct connection strings

# Initialize database
python -c "from insightdocs.models import Base, engine; Base.metadata.create_all(bind=engine)"

# Terminal 1: Start API
uvicorn insightdocs.api.main:app --reload

# Terminal 2: Start Celery worker
celery -A insightdocs.workers.celery_app worker --loglevel=info
```

## Usage Examples

### Using the CLI

```bash
# Install CLI dependencies
pip install click requests

# Check system health
python cli.py health

# Upload a document
python cli.py upload document.pdf

# Query documents
python cli.py query "What is the main topic?"

# List all documents
python cli.py list-documents

# Check task status
python cli.py status <task-id>
```

### Using curl

```bash
# Upload document
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@document.pdf"

# Query
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this about?", "top_k": 5}'

# List documents
curl "http://localhost:8000/documents/"
```

### Using Python

```python
import requests

# Upload document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/documents/upload',
        files={'file': f}
    )
    print(response.json())

# Query
response = requests.post(
    'http://localhost:8000/query/',
    json={
        'query': 'What is the main topic?',
        'top_k': 5
    }
)
print(response.json())
```

## Workflow Example

### Complete Document Processing Workflow

1. **Upload a document**:
   ```bash
   python cli.py upload my_document.pdf
   # Returns: document_id and task_id
   ```

2. **Monitor processing**:
   ```bash
   python cli.py status <task_id>
   # Check until status is "completed"
   ```

3. **Query the document**:
   ```bash
   python cli.py query "What are the key findings?"
   ```

4. **View all documents**:
   ```bash
   python cli.py list-documents
   ```

## Troubleshooting

### Services won't start

```bash
# Check if ports are already in use
lsof -i :8000  # API
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :9000  # MinIO

# Restart services
docker-compose down
docker-compose up -d
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Recreate database
docker-compose down -v
docker-compose up -d
```

### Worker not processing tasks

```bash
# Check Celery worker logs
docker-compose logs worker

# Check Redis connection
docker-compose ps redis
docker-compose logs redis
```

### OpenAI API errors

Ensure your `.env` file has a valid OpenAI API key:
```
OPENAI_API_KEY=sk-...
```

## Next Steps

- Read the [API Documentation](docs/API.md)
- Understand the [Architecture](docs/ARCHITECTURE.md)
- Explore the API at http://localhost:8000/docs

## Support

If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Verify environment variables in `.env`
3. Ensure all services are running: `docker-compose ps`
4. Open an issue on GitHub
