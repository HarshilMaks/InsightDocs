# InsightDocs System Overview

## 🎯 What is InsightDocs?

InsightDocs is a production-ready AI-driven agent architecture system that transforms unstructured documents into operational intelligence through multi-agent collaboration. Built on modern microservices patterns, it demonstrates best practices for building scalable, maintainable AI applications.

## 🌟 Key Features

### Multi-Agent Architecture
- **Orchestrator Agent**: Coordinates workflows across all agents
- **Data Agent**: Handles document ingestion, storage, and transformation
- **Analysis Agent**: Generates embeddings, summaries, and entity extraction
- **Planning Agent**: Provides workflow planning and decision support

### RAG (Retrieval-Augmented Generation)
- Document chunking and embedding generation
- Vector similarity search with FAISS
- Context-aware response generation with OpenAI
- Source citation and attribution

### Async Task Processing
- Celery workers for background processing
- Real-time task status tracking
- Progress monitoring and error handling

### Production-Ready Infrastructure
- FastAPI for high-performance APIs
- PostgreSQL for reliable data storage
- Redis for message queuing and caching
- S3/MinIO for scalable file storage
- Docker Compose for easy deployment

## 📊 System Statistics

- **35 Python modules** implementing the complete system
- **5 documentation files** covering all aspects
- **4 specialized agents** working in coordination
- **3 API routers** (documents, query, tasks)
- **Full test coverage** with pytest

## 🏗️ Architecture Layers

### 1. Presentation Layer
```
CLI Tool → FastAPI REST API → API Documentation (Swagger/ReDoc)
```

### 2. Business Logic Layer
```
Agent Orchestration → Specialized Agents → Message Queue
```

### 3. Data Layer
```
PostgreSQL (Metadata) ← → FAISS (Vectors) ← → Redis (Queue)
```

### 4. Storage Layer
```
S3/MinIO (Files) ← → Local Storage (Temp)
```

## 🔄 Data Flow Example

### Document Processing Flow
```
1. User uploads PDF via API
2. API creates Document record in PostgreSQL
3. Celery task triggers Orchestrator Agent
4. Orchestrator coordinates:
   a. Data Agent: Store file in S3, parse content
   b. Data Agent: Chunk text into segments
   c. Analysis Agent: Generate embeddings
   d. Data Agent: Store embeddings in FAISS
5. Task marked as completed
6. Document ready for querying
```

### Query Flow (RAG)
```
1. User submits query via API
2. Analysis Agent generates query embedding
3. FAISS retrieves top-k similar chunks
4. LLM Client constructs context from chunks
5. OpenAI generates contextual answer
6. Response includes answer + sources with citations
7. Query saved to history
```

## 🚀 Quick Start

### Using Docker Compose (Recommended)
```bash
# Clone and setup
git clone https://github.com/HarshilMaks/InsightOps.git
cd InsightOps
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Start all services
docker compose up -d

# Access
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - MinIO: http://localhost:9001
```

### Using CLI
```bash
# Install CLI
pip install click requests

# Upload document
python cli.py upload document.pdf

# Query
python cli.py query "What is the main topic?"

# Check status
python cli.py status <task-id>
```

## 📚 Component Details

### Agents (`insightdocs/agents/`)
- `orchestrator.py`: Central workflow coordinator
- `data_agent.py`: Data ingestion and transformation
- `analysis_agent.py`: Embeddings and content analysis
- `planning_agent.py`: Workflow planning and tracking

### API (`insightdocs/api/`)
- `main.py`: FastAPI application setup
- `documents.py`: Document management endpoints
- `query.py`: RAG query endpoints
- `tasks.py`: Task monitoring endpoints
- `schemas.py`: Pydantic request/response models

### Core (`insightdocs/core/`)
- `agent.py`: Base agent framework
- `message_queue.py`: Redis-based message passing

### Models (`insightdocs/models/`)
- `schemas.py`: SQLAlchemy database models
- `database.py`: Database connection management

### Utils (`insightdocs/utils/`)
- `document_processor.py`: Document parsing and chunking
- `embeddings.py`: Embedding generation and vector search
- `llm_client.py`: OpenAI integration

### Workers (`insightdocs/workers/`)
- `celery_app.py`: Celery configuration
- `tasks.py`: Async background tasks

### Storage (`insightdocs/storage/`)
- `file_storage.py`: S3/MinIO integration

## 🔧 Configuration

Environment variables (`.env`):
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
OPENAI_API_KEY=sk-...
S3_ENDPOINT=http://...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=insightdocs --cov-report=html

# Run specific test
pytest tests/test_core_agent.py -v
```

## 📖 Documentation

- `README.md`: Project overview and features
- `docs/QUICKSTART.md`: Getting started guide
- `docs/ARCHITECTURE.md`: Detailed system architecture
- `docs/API.md`: API endpoint reference
- `docs/DEVELOPMENT.md`: Development guide

## 🛠️ Development Tools

- `Makefile`: Common development tasks
- `cli.py`: Command-line interface
- `pytest.ini`: Test configuration
- `docker-compose.yml`: Local development environment
- `Dockerfile`: Container image definition

## 🎯 Use Cases

1. **Document Intelligence**: Upload PDFs, Word docs, text files for Q&A
2. **Knowledge Base**: Build searchable knowledge repositories
3. **Content Analysis**: Extract entities, generate summaries
4. **Workflow Automation**: Coordinate multi-step AI workflows
5. **Research Assistant**: Query across multiple documents

## 🔐 Security Features

- Environment-based configuration
- Secrets management via environment variables
- Input validation with Pydantic
- SQL injection prevention via ORM
- File upload validation

## 📈 Scalability

- Horizontal scaling of API servers
- Independent worker scaling
- Database connection pooling
- Redis clustering support
- S3 for unlimited storage

## 🚦 Performance

- Async I/O throughout
- Batch embedding generation
- Connection pooling
- Caching strategies
- Optimized vector search

## 🔄 Integration Points

- **REST API**: JSON-based HTTP API
- **Message Queue**: Redis pub/sub and queues
- **Storage**: S3-compatible object storage
- **Database**: PostgreSQL with SQLAlchemy
- **LLM**: OpenAI API (extensible to other providers)

## 🎓 Learning Resources

The codebase demonstrates:
- Async Python programming
- Agent-based architectures
- Microservices patterns
- RESTful API design
- Vector embeddings and RAG
- Celery task queues
- Docker containerization
- Test-driven development

## 🤝 Contributing

See `docs/DEVELOPMENT.md` for:
- Development workflow
- Code style guide
- Testing guidelines
- Best practices

## 📞 Support

- GitHub Issues: Bug reports and feature requests
- Documentation: Comprehensive guides in `docs/`
- Code Examples: See `cli.py` and tests

---

**Built with**: Python 3.11, FastAPI, Celery, PostgreSQL, Redis, FAISS, OpenAI, Docker
