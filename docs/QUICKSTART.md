# Quick Start Guide

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Gemini API key

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Start with Docker (Recommended)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis message broker
- MinIO object storage
- FastAPI application (port 8000)
- Celery worker

## Access Points

- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/v1/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## Manual Setup (Alternative)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Terminal 1: Start API
uvicorn backend.api.main:app --reload

# Terminal 2: Start worker
celery -A backend.workers.celery_app worker --loglevel=info
```

## Usage

### CLI Commands

```bash
# Check system health
python cli.py health

# Upload document
python cli.py upload document.pdf

# Query documents
python cli.py query "What is this about?"

# List documents
python cli.py list-documents

# Check task status
python cli.py status <task-id>
```

### REST API Examples

**Upload Document:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf"
```

**Query Documents:**
```bash
curl -X POST "http://localhost:8000/api/v1/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this about?", "top_k": 5}'
```

**Summarize Document:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/summarize"
```

**Generate Quiz:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/quiz" \
  -H "Content-Type: application/json" \
  -d '{"num_questions": 5}'
```

**Create Mind Map:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/mindmap"
```

## Supported Formats

- Text files (.txt)
- PDF documents (.pdf)
- Word documents (.docx)
- PowerPoint presentations (.pptx)
- Maximum file size: 50MB

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 8000, 5432, 6379, 9000 are available
2. **Service startup**: Check logs with `docker-compose logs`
3. **Environment**: Verify `.env` file contains valid `GEMINI_API_KEY`

### Check Service Status

```bash
# View all service logs
docker-compose logs

# Check specific service
docker-compose logs api
docker-compose logs worker
```