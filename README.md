# InsightDocs: AI-Driven Agent Architecture System

InsightDocs is an advanced agent-oriented backend system designed to automate operational intelligence, data orchestration, and planning within AI-powered environments. It enables modular, multi-agent collaboration where each agent specializes in workflow automation, analytics, or data handling through a unified backend built for scalability and clarity.

## 🎯 Project Overview

InsightDocs coordinates intelligent agents that execute contextual tasks, perform document or dataset ingestion, analyze content, and deliver structured results via APIs or dashboards. The platform emphasizes maintainability, modular design, and smooth integration with existing AI or data pipelines.

## 🏗️ Architecture

### Core System Flow

**1. Agent Orchestration**

The central Orchestrator Agent coordinates specialized sub-agents:

- **Data Agent:** Handles data ingestion, transformation, and storage
- **Analysis Agent:** Performs content extraction, summarization, and embedding computation
- **Planning Agent:** Suggests next steps, manages progress tracking, and interacts with LLMs for decision support

Agents communicate asynchronously using message queues (Redis) and follow standardized JSON schemas.

**2. Backend Logic**

- **API Layer:** FastAPI endpoints manage communication between frontend/CLI tools and the agent network
- **Worker Engine:** Celery workers process long-running ingestion, embedding, or report-generation tasks
- **Data Layer:** PostgreSQL stores metadata and user actions; FAISS indexes vector embeddings for retrieval
- **Storage Layer:** S3/MinIO handles file and output persistence

**3. Intelligence Flow**

When a user uploads data:
1. Parse → Chunk → Embed → Store → Register metadata
2. Queries route through RAG (Retrieval-Augmented Generation) engine:
   - Embed query → Retrieve top-k vectors → Construct context → Invoke LLM → Return contextual response with citations

## 🛠️ Tech Stack

- **Backend:** FastAPI, Celery, PostgreSQL, Redis
- **Embeddings & LLMs:** OpenAI / Sentence-Transformers + LangChain
- **Vector Database:** FAISS (production: Pinecone/Weaviate)
- **Storage:** MinIO / S3
- **Containerization:** Docker, Docker Compose

## 📦 Installation

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/HarshilMaks/InsightOps.git
   cd InsightOps
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Start services with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001

### Manual Installation

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up services:**
   - PostgreSQL on port 5432
   - Redis on port 6379
   - MinIO on port 9000

4. **Run migrations:**
   ```bash
   python -c "from insightdocs.models import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

5. **Start the API server:**
   ```bash
   uvicorn insightdocs.api.main:app --reload
   ```

6. **Start Celery worker:**
   ```bash
   celery -A insightdocs.workers.celery_app worker --loglevel=info
   ```

## 🚀 Usage

### Upload a Document

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Query Documents

```bash
curl -X POST "http://localhost:8000/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main topic?", "top_k": 5}'
```

### Check Task Status

```bash
curl -X GET "http://localhost:8000/tasks/{task_id}"
```

### List Documents

```bash
curl -X GET "http://localhost:8000/documents/"
```

## 📚 API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🏛️ Project Structure

```
InsightOps/
├── insightdocs/
│   ├── agents/              # Agent implementations
│   │   ├── data_agent.py
│   │   ├── analysis_agent.py
│   │   ├── planning_agent.py
│   │   └── orchestrator.py
│   ├── api/                 # FastAPI application
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── documents.py
│   │   ├── query.py
│   │   └── tasks.py
│   ├── core/                # Core framework
│   │   ├── agent.py
│   │   └── message_queue.py
│   ├── models/              # Database models
│   │   ├── database.py
│   │   └── schemas.py
│   ├── workers/             # Celery tasks
│   │   ├── celery_app.py
│   │   └── tasks.py
│   ├── utils/               # Utilities
│   │   ├── document_processor.py
│   │   ├── embeddings.py
│   │   └── llm_client.py
│   ├── storage/             # Storage layer
│   │   └── file_storage.py
│   └── config/              # Configuration
│       └── settings.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🔧 Configuration

Configuration is managed through environment variables. See `.env.example` for all available options.

Key configurations:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: OpenAI API key for LLM operations
- `S3_ENDPOINT`: S3/MinIO endpoint
- `VECTOR_DIMENSION`: Embedding dimension (default: 384)

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest tests/

# Run with coverage
pytest --cov=insightdocs tests/
```

## 🔒 Security

- Never commit `.env` files or secrets
- Use environment-specific configuration
- Rotate API keys regularly
- Use secure PostgreSQL passwords in production

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

Built with modern AI and distributed systems best practices, inspired by the InsightOps framework.

## 📞 Support

For issues and questions:
- GitHub Issues: https://github.com/HarshilMaks/InsightOps/issues
