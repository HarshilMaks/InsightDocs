# InsightDocs — Complete Project Status Report

> Full analysis of what is built, how it's built, what works, what doesn't, and what remains.
> Generated: 2026-02-28

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Codebase Statistics](#2-codebase-statistics)
3. [Architecture — Layer by Layer](#3-architecture--layer-by-layer)
4. [File-by-File Breakdown](#4-file-by-file-breakdown)
5. [What Is Built & Working](#5-what-is-built--working)
6. [What Is Built But Untested](#6-what-is-built-but-untested)
7. [What Is Not Done](#7-what-is-not-done)
8. [Known Bugs & Issues](#8-known-bugs--issues)
9. [Infrastructure & Deployment](#9-infrastructure--deployment)
10. [Remaining Work — Prioritized](#10-remaining-work--prioritized)

---

## 1. Project Overview

**InsightDocs** is an AI-driven multi-agent platform that transforms unstructured documents into queryable intelligence using RAG (Retrieval-Augmented Generation).

**Core Flow**: Upload documents (PDF, DOCX, PPTX, TXT) → AI agents parse, chunk, and embed them → Users ask questions in natural language → Get answers with source citations.

**Tech Stack**:

| Category | Technology |
|---|---|
| Language | Python 3.11+ |
| API Framework | FastAPI 0.104.1 |
| Task Queue | Celery 5.3.4 |
| Database | PostgreSQL 15 |
| Vector DB | Milvus (via pymilvus 2.4.1) |
| Cache/Broker | Redis 7 |
| Object Storage | S3 / MinIO |
| LLM | Google Gemini 1.5 Pro |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2, 384-dim) |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Containerization | Docker + Docker Compose |
| Package Manager | uv |

---

## 2. Codebase Statistics

| Metric | Count |
|---|---|
| Total Python files | 37 |
| Total lines of code | 3,230 |
| Backend modules | 29 |
| Test files | 4 |
| API routes | 19 |
| Database tables | 5 |
| AI agents | 4 |
| Celery tasks | 3 |
| Docker services | 5 |
| Environment variables | 42 |

### Lines of Code by Module

| Module | Lines | Purpose |
|---|---|---|
| `utils/embeddings.py` | 220 | Milvus vector DB + embedding generation |
| `utils/document_processor.py` | 188 | PDF/DOCX/PPTX/TXT parsing + chunking |
| `models/schemas.py` | 181 | SQLAlchemy models (5 tables) |
| `utils/llm_client.py` | 179 | Gemini LLM integration (7 methods) |
| `api/documents.py` | 167 | Document CRUD + summarize/quiz/mindmap |
| `agents/orchestrator.py` | 151 | Central workflow coordinator |
| `storage/file_storage.py` | 141 | S3/MinIO file operations |
| `agents/planning_agent.py` | 133 | Workflow planning + decision support |
| `agents/analysis_agent.py` | 131 | Embeddings + summarization + extraction |
| `workers/tasks.py` | 128 | Celery background tasks |
| `agents/data_agent.py` | 127 | Data ingestion + transformation |
| `api/schemas.py` | 123 | Pydantic request/response models |
| `cli.py` | 120 | Command-line interface |
| `core/security.py` | 111 | JWT + password hashing |
| `core/agent.py` | 103 | Base agent class + AgentMessage |
| `core/message_queue.py` | 101 | Redis pub/sub message queue |
| `api/query.py` | 101 | RAG query endpoint |
| `api/tasks.py` | 93 | Task monitoring endpoints |
| `api/auth.py` | 80 | Register + login endpoints |
| `api/main.py` | 78 | FastAPI app setup |
| `config/settings.py` | 66 | Pydantic settings (42 env vars) |

---

## 3. Architecture — Layer by Layer

### Layer 1: Presentation (Entry Points)

```
┌─────────────────────────────────────────────────────────┐
│                    Entry Points                          │
│                                                         │
│  FastAPI REST API ──── CLI (Click) ──── Swagger Docs    │
│  (port 8000)          (cli.py)         (/api/v1/docs)   │
│  /api/v1 prefix                                         │
│  CORS: localhost:3000                                    │
└─────────────────────────────────────────────────────────┘
```

**API Routers (4):**

| Router | Prefix | Endpoints | Auth Required |
|---|---|---|---|
| `auth` | `/api/v1/auth` | `POST /register`, `POST /login` | No |
| `documents` | `/api/v1/documents` | Upload, list, get, delete, summarize, quiz, mindmap | No (should be Yes) |
| `query` | `/api/v1/query` | RAG query, query history | No (should be Yes) |
| `tasks` | `/api/v1/tasks` | Get task status, list tasks | No (should be Yes) |

**All 19 Routes:**

| Method | Path | Description |
|---|---|---|
| GET | `/` | Root / health |
| GET | `/api/v1/health` | Detailed health check |
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | User login (JWT) |
| POST | `/api/v1/documents/upload` | Upload document |
| GET | `/api/v1/documents/` | List documents |
| GET | `/api/v1/documents/{id}` | Get document details |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/documents/{id}/summarize` | Generate summary |
| POST | `/api/v1/documents/{id}/quiz` | Generate quiz |
| POST | `/api/v1/documents/{id}/mindmap` | Generate mind map |
| POST | `/api/v1/query/` | RAG query |
| GET | `/api/v1/query/history` | Query history |
| GET | `/api/v1/tasks/{task_id}` | Task status |
| GET | `/api/v1/tasks/` | List tasks |
| GET | `/api/v1/docs` | Swagger UI |
| GET | `/api/v1/redoc` | ReDoc |
| GET | `/api/v1/openapi.json` | OpenAPI schema |
| GET | `/docs/oauth2-redirect` | OAuth2 redirect |

### Layer 2: Agent System

```
                    ┌──────────────────┐
                    │   Orchestrator   │  ← Routes workflows
                    │      Agent       │  ← Owns all sub-agents
                    └──┬─────┬─────┬───┘
                       │     │     │
            ┌──────────┘     │     └──────────┐
            ▼                ▼                ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │ Data Agent │   │  Analysis  │   │  Planning  │
     │            │   │   Agent    │   │   Agent    │
     │ • ingest   │   │ • embed    │   │ • suggest  │
     │ • transform│   │ • summarize│   │ • track    │
     │ • store    │   │ • extract  │   │ • decide   │
     └────────────┘   └────────────┘   └────────────┘
         │                 │                 │
    DocumentProcessor  EmbeddingEngine    LLMClient
    FileStorage        LLMClient
```

**Base Agent Contract** (`core/agent.py`):
- All agents inherit from `BaseAgent`
- Standard interface: `async process(message: Dict) -> Dict`
- Built-in: structured JSON logging, error handling with context
- `AgentMessage` class for inter-agent communication (type, payload, sender, recipient, correlation_id)

**Message Queue** (`core/message_queue.py`):
- Redis-based pub/sub + list queues
- `publish()`, `enqueue()`, `dequeue()` operations
- Currently NOT used — orchestrator calls agents directly via `await`
- Infrastructure ready for future decoupling

### Layer 3: Async Workers (Celery)

| Task | Name | Trigger | What It Does |
|---|---|---|---|
| `process_document_task` | `insightdocs.process_document` | Document upload | Full pipeline: ingest → chunk → embed → store → summarize |
| `generate_embeddings_task` | `insightdocs.generate_embeddings` | On demand | Standalone embedding generation |
| `cleanup_old_tasks` | `insightdocs.cleanup_old_tasks` | Periodic | Deletes tasks older than 30 days |

**Celery Config:**
- Broker: Redis
- Backend: Redis
- Serializer: JSON
- Task time limit: 3600s (1 hour)
- Soft time limit: 3300s (55 min)
- Async fix: `asyncio.run()` wrapper for async agent calls

### Layer 4: Data Storage

**PostgreSQL — 5 Tables:**

| Table | Primary Key | Key Fields | Relationships |
|---|---|---|---|
| `users` | UUID (string) | email, name, hashed_password, is_active | → documents, queries, tasks |
| `documents` | UUID (string) | filename, file_type, file_size, s3_bucket, s3_key, status | → user, chunks, tasks |
| `document_chunks` | UUID (string) | document_id, chunk_index, content, milvus_id | → document |
| `tasks` | UUID (string) | task_type, status, progress, result (JSON), error | → user, document |
| `queries` | UUID (string) | query_text, response_text, response_time, confidence_score, tokens_used, sources (JSON) | → user |

All tables use `TimestampMixin` (created_at, updated_at with timezone).

**Milvus — Vector Collection:**

| Field | Type | Notes |
|---|---|---|
| `id` | VARCHAR(100) | Primary key (UUID) |
| `document_id` | VARCHAR(100) | Links to PostgreSQL |
| `text` | VARCHAR(65535) | Original chunk text |
| `vector` | FLOAT_VECTOR(384) | IVF_FLAT index, COSINE metric, nlist=128 |

**Redis**: Celery broker (db 0) + result backend (db 1) + message queue infrastructure.

**S3/MinIO**: Raw files under `documents/` prefix. Auto-creates bucket. Presigned URL support.

### Layer 5: LLM & Embeddings

**LLMClient** (7 methods):

| Method | Used By | Purpose |
|---|---|---|
| `summarize()` | AnalysisAgent, `/summarize` endpoint | Document summarization |
| `extract_entities()` | AnalysisAgent | Named entity extraction |
| `generate_rag_response()` | Query endpoint | RAG answer generation |
| `generate_quiz()` | `/quiz` endpoint | Multiple-choice quiz generation |
| `generate_mindmap()` | `/mindmap` endpoint | Concept + relationship extraction |
| `generate_suggestions()` | PlanningAgent | Next-step suggestions |
| `recommend_option()` | PlanningAgent | Decision support |

**EmbeddingEngine**:
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- `embed_texts()` → batch encode
- `store_embeddings()` → insert into Milvus
- `search()` → cosine similarity search, returns top_k results

---

## 4. File-by-File Breakdown

### Backend Core

| File | Status | What It Does |
|---|---|---|
| `core/agent.py` | ✅ Complete | BaseAgent ABC + AgentMessage dataclass |
| `core/message_queue.py` | ✅ Complete (unused) | Redis pub/sub + list queue operations |
| `core/security.py` | ✅ Complete | Password hashing, JWT create/decode, `get_current_user` dependency |
| `config/settings.py` | ✅ Complete | 42 env vars via Pydantic Settings |
| `models/database.py` | ✅ Complete | SQLAlchemy engine + session factory |
| `models/schemas.py` | ✅ Complete | 5 ORM models + TaskStatus enum |

### Agents

| File | Status | What It Does |
|---|---|---|
| `agents/orchestrator.py` | ✅ Complete | Coordinates ingest_and_analyze + query workflows, stores chunks to DB, auto-summarizes |
| `agents/data_agent.py` | ✅ Complete | Ingest (S3 upload + parse), transform (chunk), store (placeholder) |
| `agents/analysis_agent.py` | ✅ Complete | Embed, summarize, extract entities |
| `agents/planning_agent.py` | ✅ Complete | Suggest steps, track progress, decision support |

### API

| File | Status | What It Does |
|---|---|---|
| `api/main.py` | ✅ Complete | FastAPI app, CORS, router registration |
| `api/auth.py` | ✅ Complete | Register + login endpoints |
| `api/documents.py` | ✅ Complete | CRUD + summarize/quiz/mindmap endpoints |
| `api/query.py` | ✅ Complete | RAG query + history |
| `api/tasks.py` | ✅ Complete | Task status + list |
| `api/schemas.py` | ✅ Complete | 15 Pydantic models |

### Utilities

| File | Status | What It Does |
|---|---|---|
| `utils/document_processor.py` | ✅ Complete | TXT, PDF (PyPDF2), DOCX (python-docx), PPTX (python-pptx) parsing + chunking |
| `utils/embeddings.py` | ✅ Complete | Milvus connection, embedding generation, vector search |
| `utils/llm_client.py` | ✅ Complete | 7 Gemini methods (summarize, quiz, mindmap, RAG, entities, suggestions, recommend) |

### Workers

| File | Status | What It Does |
|---|---|---|
| `workers/celery_app.py` | ✅ Complete | Celery config with Redis broker |
| `workers/tasks.py` | ✅ Complete | 3 tasks with asyncio.run() fix, document status updates |

### Storage

| File | Status | What It Does |
|---|---|---|
| `storage/file_storage.py` | ✅ Complete | S3/MinIO upload, download, delete, presigned URLs |

### Other

| File | Status | What It Does |
|---|---|---|
| `cli.py` | ⚠️ Partial | Upload, query, list, status, health — but URLs don't include `/api/v1` prefix |
| `Dockerfile` | ✅ Complete | Python 3.11-slim + uv |
| `docker-compose.yml` | ✅ Complete | 5 services (postgres, redis, minio, api, worker) |

### Tests

| File | Status | Coverage |
|---|---|---|
| `tests/conftest.py` | ⚠️ Broken | Uses `monkeypatch` with `session` scope (not allowed in pytest) |
| `tests/test_api.py` | ⚠️ Broken | Tests `/health` and `/docs` without `/api/v1` prefix |
| `tests/test_core_agent.py` | ✅ Works | BaseAgent + AgentMessage tests |
| `tests/test_document_processor.py` | ✅ Works | Chunking + TXT parsing tests |

### Frontend

| File | Status |
|---|---|
| `frontend/package.json` | ❌ Empty (0 bytes) |
| `frontend/src/components/ChatUI.js` | ❌ Empty |
| `frontend/src/css/style.css` | ❌ Empty |
| `frontend/src/js/main.js` | ❌ Empty |
| `frontend/src/pages/index.js` | ❌ Empty |
| `frontend/src/assets/logo.png` | ❌ Empty |

**Frontend is completely unbuilt.** Directory structure exists as placeholder only.

---

## 5. What Is Built & Working (Verified)

| Component | How Verified |
|---|---|
| ✅ PDF parsing (PyPDF2) | Tested with generated PDF — extracts text page-by-page |
| ✅ DOCX parsing (python-docx) | Tested — extracts paragraphs + table content |
| ✅ PPTX parsing (python-pptx) | Tested — extracts slide-by-slide with labels |
| ✅ TXT parsing | Tested — reads file content |
| ✅ Text chunking with overlap | Tested — sentence-aware splitting works correctly |
| ✅ File type validation | 6 supported extensions enforced |
| ✅ File size validation | 50MB limit enforced |
| ✅ FastAPI app loads | All 19 routes registered and accessible |
| ✅ All imports resolve | Every module imports without errors |
| ✅ All files syntax-valid | AST parsing passes on all 37 Python files |
| ✅ Dependencies installed | PyPDF2, python-docx, python-pptx + all existing deps |
| ✅ BaseAgent framework | Process interface, error handling, logging |
| ✅ AgentMessage serialization | to_dict / from_dict round-trip |

---

## 6. What Is Built But Untested (Needs Running Services)

These components have code written but need PostgreSQL, Redis, Milvus, MinIO, and Gemini API to test:

| Component | Depends On | Risk Level |
|---|---|---|
| Full upload → process → embed pipeline | All services | Medium — async flow is complex |
| Celery worker task execution | Redis, PostgreSQL | Medium — asyncio.run() wrapper untested in Celery |
| Milvus vector storage + search | Milvus server | Low — standard pymilvus usage |
| S3/MinIO file upload | MinIO | Low — standard boto3 usage |
| RAG query end-to-end | Milvus, Gemini | Medium — multiple components chained |
| Summarize endpoint | PostgreSQL, Gemini | Low — simple LLM call |
| Quiz generation endpoint | PostgreSQL, Gemini | Low — LLM call + JSON parsing |
| Mind map endpoint | PostgreSQL, Gemini | Low — LLM call + JSON parsing |
| Auth register/login | PostgreSQL | Low — standard JWT flow |
| Chunk persistence to PostgreSQL | PostgreSQL | Low — standard ORM insert |
| Document status updates | PostgreSQL | Low — simple field updates |
| Task status tracking | PostgreSQL, Redis | Low |

---

## 7. What Is Not Done

### Not Built At All

| Feature | Priority | Effort |
|---|---|---|
| **Frontend** | High | Large — entire React/Vue app needed |
| **Image/OCR support** | Medium | Medium — integrate Tesseract or cloud vision |
| **eBook (.epub) parsing** | Low | Low — add ebooklib |
| **Podcast generation (TTS)** | Low | Medium — integrate TTS service |
| **Presentation generation** | Low | Medium — python-pptx output |
| **Auth enforcement on endpoints** | High | Low — add `Depends(get_current_user)` |
| **Database migrations (Alembic)** | High | Low — `alembic init` + generate migrations |
| **Rate limiting** | Medium | Low — add slowapi or similar |
| **Webhook notifications** | Low | Medium |
| **Real health checks** | Medium | Low — actually ping DB/Redis/Milvus |

### Partially Built

| Feature | What Exists | What's Missing |
|---|---|---|
| **Auth** | Register, login, JWT, `get_current_user` dependency | Not enforced on any endpoint — `user_id="system"` hardcoded |
| **CLI** | 5 commands (upload, query, list, status, health) | URLs missing `/api/v1` prefix, no auth token support |
| **Message Queue** | Full Redis pub/sub implementation | Not used — agents called directly |
| **`.doc` (old Word)** | Route exists in parser | python-docx can't read `.doc` format, only `.docx` |
| **Planning Agent** | suggest_steps, track_progress, make_decision | track_progress only logs, doesn't persist anywhere |
| **Data Agent store** | Task type handler exists | Returns placeholder, doesn't actually store |
| **Orchestrator query workflow** | Handler exists | Returns placeholder string, real RAG is in query endpoint |
| **Tests** | 4 test files, ~200 lines | conftest broken, API tests use wrong URL prefix, no integration tests |

---

## 8. Known Bugs & Issues

| # | Severity | Issue | File | Fix |
|---|---|---|---|---|
| 1 | **High** | `conftest.py` uses `monkeypatch` with `session` scope — pytest doesn't allow this | `tests/conftest.py` | Change to `function` scope or use `monkeypatch_session` |
| 2 | **High** | API tests hit `/health` and `/docs` instead of `/api/v1/health` and `/api/v1/docs` | `tests/test_api.py` | Update URL paths |
| 3 | **High** | CLI uses `http://localhost:8000/documents/upload` instead of `/api/v1/documents/upload` | `cli.py` | Add `/api/v1` to `API_BASE_URL` |
| 4 | **Medium** | `tasks.py` creates Task records but upload endpoint doesn't create a Task row first | `backend/api/documents.py` | Task lookup in worker will return None |
| 5 | **Medium** | `.doc` files routed to `_parse_word_file()` but python-docx can't read old `.doc` format | `document_processor.py` | Remove `.doc` from supported or add antiword |
| 6 | **Medium** | `DocumentListResponse` expects `DocumentResponse` objects with `user_id` field — list endpoint may fail if user_id is missing | `backend/api/documents.py` | Verify ORM → Pydantic serialization |
| 7 | **Low** | Health endpoint returns hardcoded "healthy" — doesn't actually check services | `backend/api/main.py` | Add real DB/Redis/Milvus pings |
| 8 | **Low** | `EmbeddingEngine.__init__` sets `self.collection = None` before `_init_collection` checks it | `backend/utils/embeddings.py` | Initialize collection field before connect |
| 9 | **Low** | Query endpoint creates `EmbeddingEngine()` on every request (loads model each time) | `backend/api/query.py` | Use dependency injection or singleton |

---

## 9. Infrastructure & Deployment

### Docker Compose Services

| Service | Image | Ports | Health Check |
|---|---|---|---|
| `postgres` | postgres:15 | 5432 | `pg_isready` |
| `redis` | redis:7-alpine | 6379 | `redis-cli ping` |
| `minio` | minio/minio | 9000, 9001 | curl health endpoint |
| `api` | Custom (Dockerfile) | 8000 | None |
| `worker` | Custom (Dockerfile) | None | None |

**Volumes**: `postgres_data`, `minio_data` (persistent)

**Docker networking**: Services reference each other by name (postgres, redis, minio). Environment overrides in docker-compose.yml handle internal URLs.

### Environment Variables (42 total)

| Category | Variables |
|---|---|
| App | APP_NAME, APP_ENV, APP_PORT, API_PREFIX, DEBUG, LOG_LEVEL, SECRET_KEY |
| Database | DATABASE_URL, DATABASE_POOL_SIZE, POSTGRES_USER/PASSWORD/DB/PORT |
| Redis | REDIS_URL, REDIS_PORT |
| Celery | CELERY_BROKER_URL, CELERY_RESULT_BACKEND |
| LLM | GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE |
| Milvus | MILVUS_URI, MILVUS_TOKEN, MILVUS_COLLECTION, MILVUS_DIM, MILVUS_METRIC |
| Storage | S3_ENDPOINT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, MINIO_* |
| Auth | ACCESS_TOKEN_EXPIRE_MINUTES, ALLOWED_ORIGINS |
| Frontend | REACT_APP_API_URL |
| Other | MAX_FILE_SIZE, VECTOR_DIMENSION, REQUEST_TIMEOUT, REQUIRE_HTTPS, METRICS_ENABLED, TOKEN_LOGGING, LAMBDA_FUNCTION_NAME |

---

## 10. Remaining Work — Prioritized

### P0 — Must Fix Before Running

| # | Task | Effort | Files |
|---|---|---|---|
| 1 | Fix CLI to use `/api/v1` prefix | 5 min | `cli.py` |
| 2 | Create Task record in upload endpoint (so worker can find it) | 10 min | `backend/api/documents.py` |
| 3 | Fix test conftest scope + API test URLs | 10 min | `tests/conftest.py`, `tests/test_api.py` |
| 4 | Remove `.doc` from supported extensions (or handle gracefully) | 5 min | `backend/utils/document_processor.py` |
| 5 | Initialize `self.collection` properly in EmbeddingEngine | 5 min | `backend/utils/embeddings.py` |
| 6 | Run `docker-compose up` and do end-to-end test | 30 min | — |

### P1 — Should Do Soon

| # | Task | Effort | Files |
|---|---|---|---|
| 7 | Enforce auth on document/query/task endpoints | 30 min | `backend/api/documents.py`, `query.py`, `tasks.py` |
| 8 | Set up Alembic for database migrations | 20 min | New `alembic/` directory |
| 9 | Make EmbeddingEngine a singleton / use dependency injection | 15 min | `backend/utils/embeddings.py`, `backend/api/query.py` |
| 10 | Add real health checks (ping DB, Redis, Milvus) | 20 min | `backend/api/main.py` |

### P2 — Feature Additions

| # | Task | Effort |
|---|---|---|
| 11 | Build frontend (React + drag-and-drop upload + chat UI) | Large |
| 12 | Add image/OCR support | Medium |
| 13 | Add eBook (.epub) parsing | Small |
| 14 | Add podcast generation (TTS) | Medium |
| 15 | Add presentation export (.pptx output) | Medium |

---

*End of report.*
