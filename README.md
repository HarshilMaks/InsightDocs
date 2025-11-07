# InsightDocs

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

> An AI-driven agent architecture system for transforming unstructured documents into operational intelligence through multi-agent collaboration and RAG (Retrieval-Augmented Generation).

## 🎯 Overview

InsightDocs (formerly InsightDocs) is a production-ready platform that combines multi-agent AI architecture with RAG capabilities to process, analyze, and query documents intelligently. Built with modern microservices patterns, it demonstrates best practices for building scalable, maintainable AI applications.

### Key Capabilities

- **📄 Document Intelligence**: Upload and process PDFs, Word documents, and text files
- **🤖 Multi-Agent System**: Coordinated AI agents working together on complex workflows
- **🔍 Semantic Search**: RAG-powered queries with vector similarity search
- **⚡ Async Processing**: Background task processing with Celery workers
- **🎨 REST API**: FastAPI-based high-performance API endpoints
- **🐳 Docker Ready**: Complete containerized deployment stack

## 🌟 Features

### Multi-Agent Architecture

The system employs four specialized agents coordinated by an orchestrator:

- **Orchestrator Agent**: Central workflow coordinator managing all agents
- **Data Agent**: Handles document ingestion, storage, and transformation
- **Analysis Agent**: Generates embeddings, summaries, and entity extraction
- **Planning Agent**: Provides workflow planning and decision support

### RAG (Retrieval-Augmented Generation)

- Document chunking and intelligent segmentation
- Vector embedding generation with sentence transformers
- FAISS-powered similarity search
- Context-aware response generation using OpenAI
- Source citation and attribution

### Production Infrastructure

- **FastAPI**: High-performance async API framework
- **PostgreSQL**: Reliable metadata and document storage
- **Redis**: Message queuing, task broker, and caching
- **S3/MinIO**: Scalable object storage for files
- **Celery**: Distributed async task processing
- **Docker Compose**: Simple deployment orchestration

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Presentation Layer                    │
│  CLI Tool  │  FastAPI REST API  │  API Docs (Swagger)      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                    │
│  Orchestrator → Data Agent → Analysis Agent → Planning Agent│
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                         Data Layer                           │
│  PostgreSQL (Metadata) ↔ FAISS (Vectors) ↔ Redis (Queue)  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       Storage Layer                          │
│        S3/MinIO (Files) ↔ Local Storage (Temp)            │
└─────────────────────────────────────────────────────────────┘
```

### Workflow Example: Document Processing

```
User → API → Document Record (PostgreSQL)
           → Celery Task → Orchestrator Agent
                         → Data Agent: Store file in S3, parse content
                         → Data Agent: Chunk text into segments
                         → Analysis Agent: Generate embeddings
                         → Data Agent: Store in FAISS
           → Task Complete → Document ready for querying
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- OpenAI API key

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
```

2. **Configure environment**

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. **Start with Docker Compose (Recommended)**

```bash
docker-compose up -d
```

Services will be available at:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (credentials: minioadmin/minioadmin)

### Alternative: Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start services (PostgreSQL, Redis, MinIO separately)

# Initialize database
python -c "from insightdocs.models import Base, engine; Base.metadata.create_all(bind=engine)"

# Terminal 1: Start API
uvicorn insightdocs.api.main:app --reload

# Terminal 2: Start Celery worker
celery -A insightdocs.workers.celery_app worker --loglevel=info
```

## 💡 Usage Examples

### Using the CLI

```bash
# Check system health
python cli.py health

# Upload a document
python cli.py upload document.pdf

# Query documents
python cli.py query "What are the key findings?"

# List all documents
python cli.py list-documents

# Check task status
python cli.py status <task-id>
```

### Using the REST API

**Upload a document:**

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@document.pdf"
```

**Query documents:**

```bash
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this about?", "top_k": 5}'
```

**List documents:**

```bash
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
    result = response.json()
    print(f"Document ID: {result['document_id']}")
    print(f"Task ID: {result['task_id']}")

# Query documents
response = requests.post(
    'http://localhost:8000/query/',
    json={'query': 'What are the main topics?', 'top_k': 5}
)
answer = response.json()
print(f"Answer: {answer['answer']}")
print(f"Sources: {len(answer['sources'])} chunks retrieved")
```

## 📦 Project Structure

```
InsightDocs/
├── insightdocs/           # Main application package
│   ├── agents/            # Multi-agent system
│   │   ├── orchestrator.py    # Central coordinator
│   │   ├── data_agent.py      # Data operations
│   │   ├── analysis_agent.py  # Analysis & embeddings
│   │   └── planning_agent.py  # Workflow planning
│   ├── api/               # FastAPI endpoints
│   │   ├── main.py            # Application entry
│   │   ├── documents.py       # Document management
│   │   ├── query.py           # RAG query endpoint
│   │   ├── tasks.py           # Task monitoring
│   │   └── schemas.py         # Pydantic models
│   ├── core/              # Core framework
│   │   ├── agent.py           # Base agent class
│   │   └── message_queue.py   # Message passing
│   ├── models/            # Database models
│   │   ├── schemas.py         # SQLAlchemy models
│   │   └── database.py        # DB connection
│   ├── utils/             # Utilities
│   │   ├── document_processor.py  # Document parsing
│   │   ├── embeddings.py          # Vector operations
│   │   └── llm_client.py          # OpenAI integration
│   ├── workers/           # Celery workers
│   │   ├── celery_app.py      # Celery config
│   │   └── tasks.py           # Background tasks
│   ├── storage/           # Storage layer
│   │   └── file_storage.py    # S3/MinIO integration
│   └── config/            # Configuration
│       └── settings.py        # App settings
├── tests/                 # Test suite
├── docs/                  # Documentation
├── cli.py                 # Command-line interface
├── docker-compose.yml     # Docker orchestration
├── Dockerfile             # Container definition
├── Makefile               # Development commands
└── requirements.txt       # Dependencies
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=insightdocs --cov-report=html

# Run specific test module
pytest tests/test_core_agent.py -v
```

## 🛠️ Development

### Using Make Commands

```bash
make help           # Show all available commands
make install        # Install production dependencies
make install-dev    # Install development dependencies
make test           # Run test suite
make test-cov       # Run tests with coverage
make clean          # Clean cache and temp files
make run-api        # Start API server
make run-worker     # Start Celery worker
make docker-up      # Start all services
make docker-down    # Stop all services
make docker-logs    # View service logs
```

### Development Workflow

1. Create a feature branch
2. Make changes and test locally
3. Run tests: `make test`
4. Clean up: `make clean`
5. Submit pull request

## 📚 Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)**: Getting started with InsightDocs
- **[Architecture Guide](docs/ARCHITECTURE.md)**: Deep dive into system design
- **[API Reference](docs/API.md)**: Complete API endpoint documentation
- **[Development Guide](docs/DEVELOPMENT.md)**: Contributing and development workflow
- **[System Overview](SYSTEM_OVERVIEW.md)**: Detailed component breakdown

## ⚙️ Configuration

Environment variables (`.env` file):

```bash
# Database
DATABASE_URL=postgresql://insightdocs:insightdocs@localhost:5432/insightdocs

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# OpenAI
OPENAI_API_KEY=sk-your-api-key-here

# Storage (S3/MinIO)
S3_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=insightdocs

# Application
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here

# Vector Database
VECTOR_DIMENSION=384
```

## 🎯 Use Cases

1. **Document Intelligence Platform**: Build Q&A systems over document collections
2. **Knowledge Base Management**: Create searchable organizational knowledge repositories
3. **Research Assistant**: Query and analyze across multiple research documents
4. **Content Analysis**: Extract entities, generate summaries, analyze document content
5. **Workflow Automation**: Coordinate complex multi-step AI-powered workflows

## 🔒 Security Features

- Environment-based configuration for sensitive data
- Pydantic input validation on all endpoints
- SQL injection prevention via SQLAlchemy ORM
- File upload validation and sanitization
- Secrets management via environment variables

## 📈 Performance & Scalability

- **Async I/O**: Non-blocking operations throughout the stack
- **Connection Pooling**: Efficient database connection management
- **Batch Processing**: Optimized embedding generation
- **Horizontal Scaling**: Scale API servers and workers independently
- **Caching**: Redis-based caching for frequently accessed data
- **Vector Search**: FAISS for fast similarity search at scale

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| **Language** | Python 3.11+ |
| **API Framework** | FastAPI |
| **Task Queue** | Celery |
| **Database** | PostgreSQL |
| **Cache/Queue** | Redis |
| **Vector DB** | FAISS |
| **Storage** | S3/MinIO |
| **LLM** | OpenAI GPT |
| **Embeddings** | Sentence Transformers |
| **Containerization** | Docker, Docker Compose |

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure your code:
- Follows the existing code style
- Includes appropriate tests
- Updates documentation as needed
- Passes all tests (`make test`)

## 🐛 Troubleshooting

### Services won't start

```bash
# Check if ports are in use
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
# Check PostgreSQL
docker-compose ps postgres
docker-compose logs postgres

# Recreate database
docker-compose down -v
docker-compose up -d
```

### Worker not processing tasks

```bash
# Check worker logs
docker-compose logs worker

# Check Redis
docker-compose ps redis
```

## 📊 Project Statistics

- **29 Python modules** implementing the complete system
- **2,271 lines of code** in the main application
- **200+ lines** of test coverage
- **4 specialized agents** working in coordination
- **3 API routers** (documents, query, tasks)
- **5 documentation files** covering all aspects

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with modern Python frameworks and best practices
- Inspired by agent-based architectures and microservices patterns
- Demonstrates practical implementation of RAG systems

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/HarshilMaks/InsightDocs/issues)
- **Documentation**: See the `docs/` directory
- **Examples**: Check out `cli.py` for usage examples

---

**Built with ❤️ using Python, FastAPI, Celery, PostgreSQL, Redis, FAISS, and OpenAI**
