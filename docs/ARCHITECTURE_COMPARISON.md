# InsightDocs — Architecture & Competitive Comparison

> A detailed analysis of InsightDocs' system architecture, workflows, and feature comparison against consumer AI document tools (e.g., AI PDF Summarizer platforms).

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Core Workflows](#2-core-workflows)
3. [Feature Comparison](#3-feature-comparison-insightdocs-vs-ai-pdf-summarizer)
4. [Strengths & Gaps](#4-strengths--gaps)
5. [Integration Feasibility](#5-integration-feasibility)
6. [Key Design Decisions](#6-key-design-decisions)
7. [Conclusion](#7-conclusion)

---

## 1. System Architecture

InsightDocs is built as a **multi-agent AI platform** using microservices patterns. The system is organized into five distinct layers.

### Layer 1 — Presentation (Entry Points)

| Entry Point | Technology | Description |
|---|---|---|
| REST API | FastAPI on port 8000 | Primary interface, prefixed at `/api/v1` |
| CLI | Click (Python) | Command-line tool for upload, query, list, health |
| API Docs | Swagger UI | Auto-generated at `/api/v1/docs` |

**API Routers:**

| Router | Purpose |
|---|---|
| `auth` | User registration & login (JWT with access + refresh tokens) |
| `documents` | Upload, list, get, delete documents |
| `query` | RAG-powered queries + query history |
| `tasks` | Background task status monitoring |

### Layer 2 — Agent System (The Brain)

The core of InsightDocs is a **multi-agent orchestration** pattern. All agents inherit from `BaseAgent`, which provides a standard `async process(message)` interface, structured JSON logging, and error handling.

```
                    ┌──────────────────┐
                    │   Orchestrator   │  ← Central coordinator
                    │      Agent       │
                    └──┬─────┬─────┬───┘
                       │     │     │
            ┌──────────┘     │     └──────────┐
            ▼                ▼                ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │ Data Agent │   │  Analysis  │   │  Planning  │
     │            │   │   Agent    │   │   Agent    │
     └────────────┘   └────────────┘   └────────────┘
```

| Agent | Dependencies | Capabilities |
|---|---|---|
| **Orchestrator** | All sub-agents | Routes workflows (`ingest_and_analyze`, `query`), coordinates multi-step pipelines |
| **Data Agent** | DocumentProcessor, FileStorage | File ingestion (S3), document parsing, text chunking (sentence-aware with overlap) |
| **Analysis Agent** | EmbeddingEngine, LLMClient | Embedding generation, text summarization, named entity extraction |
| **Planning Agent** | LLMClient | Next-step suggestions, progress tracking, decision support |

**Inter-Agent Communication:**
A `MessageQueue` class exists using Redis pub/sub and list-based queues with `AgentMessage` objects. In practice, the orchestrator currently calls agents directly via `await`. The queue infrastructure is ready for future decoupling.

### Layer 3 — Async Workers (Celery)

Background processing via Celery with Redis as the message broker.

| Task | Trigger | Description |
|---|---|---|
| `process_document_task` | Document upload | Runs the full `ingest_and_analyze` pipeline via the Orchestrator |
| `generate_embeddings_task` | On demand | Standalone embedding generation for document chunks |
| `cleanup_old_tasks` | Periodic (scheduled) | Removes completed/failed tasks older than 30 days |

### Layer 4 — Data Storage

| Store | Technology | Purpose |
|---|---|---|
| **Relational DB** | PostgreSQL | Metadata, auth, task tracking, query history |
| **Vector DB** | Milvus | Document embeddings with COSINE similarity search |
| **Message Broker** | Redis | Celery broker, result backend, message queue |
| **Object Storage** | S3 / MinIO | Raw document files, presigned URL access |

**PostgreSQL Schema (5 tables):**

| Table | Key Fields |
|---|---|
| `users` | id, email, name, hashed_password, is_active |
| `documents` | id, filename, file_type, file_size, s3_bucket, s3_key, status, user_id |
| `document_chunks` | id, document_id, chunk_index, content, milvus_id |
| `tasks` | id, task_type, status, progress, result, error, user_id, document_id |
| `queries` | id, query_text, response_text, response_time, confidence_score, tokens_used, sources |

All models use UUID primary keys and a `TimestampMixin` (created_at, updated_at).

**Milvus Collection Schema:**

| Field | Type | Notes |
|---|---|---|
| `id` | VARCHAR | Primary key |
| `document_id` | VARCHAR | Links back to PostgreSQL |
| `text` | VARCHAR | Original chunk text |
| `vector` | FLOAT_VECTOR (384-dim) | IVF_FLAT index, COSINE metric |

### Layer 5 — LLM & Embedding Integration

| Component | Technology | Details |
|---|---|---|
| **LLM** | Google Gemini 1.5 Pro | Summarization, entity extraction, RAG responses, suggestions, decision support |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) | 384-dimensional vectors for semantic search |

---

## 2. Core Workflows

### Workflow 1 — Document Upload & Processing

```
User uploads file via POST /api/v1/documents/upload
    │
    ▼
API saves file to temp disk
Creates Document record in PostgreSQL (status: PENDING)
    │
    ▼
Fires Celery task: process_document_task
Returns task_id immediately to user (non-blocking)
    │
    ▼
Celery Worker picks up task ──────────────────────────────────────
    │
    ▼
OrchestratorAgent.process(workflow_type="ingest_and_analyze")
    │
    ├── Step 1: DataAgent.ingest()
    │     • FileStorage uploads file to S3/MinIO
    │     • DocumentProcessor parses file content
    │
    ├── Step 2: DataAgent.transform()
    │     • Sentence-aware text chunking
    │     • Configurable chunk_size (default: 1000) and overlap (default: 200)
    │
    ├── Step 3: AnalysisAgent.embed()
    │     • SentenceTransformer generates 384-dim vectors
    │     • Vectors stored in Milvus collection
    │
    └── Step 4: PlanningAgent.track_progress()
          • Logs completion statistics
          • Task status updated to COMPLETED in PostgreSQL
```

### Workflow 2 — RAG Query

```
User sends POST /api/v1/query/ with { query, top_k }
    │
    ▼
EmbeddingEngine.search(query_text, top_k)
    • Encodes query using same SentenceTransformer model
    • COSINE similarity search in Milvus
    • Returns top_k matching chunks with scores
    │
    ▼
LLMClient.generate_rag_response(query, context_chunks)
    • Constructs prompt: context chunks + user question
    • Gemini generates grounded answer
    │
    ▼
Saves query + response to PostgreSQL (queries table)
    │
    ▼
Returns to user:
    • answer (LLM-generated)
    • sources (matched chunks with metadata & distance scores)
    • metadata (top_k, sources_count)
```

---

## 3. Feature Comparison: InsightDocs vs AI PDF Summarizer

| Feature | AI PDF Summarizer | InsightDocs | Status |
|---|---|---|---|
| **PDF Upload & Parsing** | ✅ Full extraction | ⚠️ Placeholder (returns hardcoded string) | **Critical gap** |
| **Image Upload (OCR)** | ✅ Vision-based | ❌ Not supported | Missing |
| **PPT Support** | ✅ | ❌ Not supported | Missing |
| **Word (.docx) Support** | ✅ | ⚠️ Placeholder | Gap |
| **TXT Support** | ✅ | ✅ Fully working | **Parity** |
| **eBook Support** | ✅ | ❌ Not supported | Missing |
| **File Size Validation** | ✅ 50MB limit | ❌ No validation | Minor gap |
| **Summary Generation** | ✅ Core feature | ⚠️ Code exists (`LLMClient.summarize`), not wired to pipeline | Plumbing exists |
| **Mind Map** | ✅ Visual knowledge graph | ❌ Nothing equivalent | Missing |
| **AI Chat (RAG)** | ✅ Chat with documents | ✅ Full RAG pipeline working | **Parity** |
| **Generate Podcast** | ✅ Audio from document | ❌ No audio generation | Missing |
| **Generate Presentation** | ✅ Slides from content | ❌ No slide generation | Missing |
| **Generate Quiz** | ✅ Questions from content | ❌ No quiz generation | Missing |
| **Drag & Drop UI** | ✅ Polished frontend | ❌ Frontend directory exists but empty | Missing |

### Comparison Summary

```
AI PDF Summarizer:
    Document → [ Black Box AI ] → Summary / Mind Map / Quiz / Podcast / Slides
                                   (many output formats, single pipeline)

InsightDocs:
    Document → [ Orchestrator → Data Agent → Analysis Agent → Planning Agent ]
                → Stored in Milvus → RAG Query
                (one output format, sophisticated multi-agent pipeline)
```

---

## 4. Strengths & Gaps

### What InsightDocs Has That They Likely Don't

| Strength | Details |
|---|---|
| **Multi-agent architecture** | Extensible to new agent types without restructuring |
| **Async task processing** | Handles large files without blocking the API |
| **Task monitoring** | Users can poll processing status in real-time |
| **Query history & analytics** | Response time, confidence score, token usage tracked per query |
| **User auth infrastructure** | JWT-based auth with user-scoped data (partially wired) |
| **Production-grade storage** | S3/MinIO + Milvus + PostgreSQL (scalable, persistent) |
| **Horizontal scalability** | API servers and Celery workers scale independently |
| **Message queue infrastructure** | Redis-based, ready for agent decoupling |

### Critical Gaps to Address

| Gap | Severity | Effort to Fix |
|---|---|---|
| PDF parsing is a placeholder | **Critical** | Low — integrate `PyPDF2` or `pdfplumber` |
| DOCX parsing is a placeholder | **High** | Low — integrate `python-docx` |
| No summary endpoint exposed | **High** | Low — wire existing `LLMClient.summarize()` to a new route |
| No file size validation | **Medium** | Trivial — add check in upload endpoint |
| Auth not enforced on endpoints | **Medium** | Low — add dependency injection for current user |
| Celery sync/async mismatch | **Medium** | Low — wrap async calls with `asyncio.run()` |
| No frontend | **High** | Medium — build React/Vue app (CORS already configured) |
| No image/OCR support | **Medium** | Medium — integrate Tesseract or cloud vision API |
| No quiz/podcast/slides generation | **Low** (for now) | Medium — new LLM prompts + output formatters |

---

## 5. Integration Feasibility

Can InsightDocs evolve to match that product? **Yes.** Here's what each feature would require:

| Target Feature | What Exists | What's Needed |
|---|---|---|
| **PDF Summarizer** | `LLMClient.summarize()`, upload pipeline | Fix PDF parsing, add `/summarize` endpoint (~30 lines) |
| **Mind Map** | LLM integration, entity extraction | New LLM prompt to extract concepts + relationships, return structured JSON, frontend renderer |
| **AI Chat** | Full RAG pipeline | **Already working** — closest feature match |
| **Quiz Generation** | LLM integration, Planning Agent | New method on `LLMClient` with quiz prompt, new endpoint |
| **Podcast Generation** | LLM summarization | Add TTS integration (Google Cloud TTS / ElevenLabs), new endpoint |
| **Presentation Generation** | LLM integration | LLM extracts key points → `python-pptx` generates .pptx, new endpoint |

### Architectural Advantage

The multi-agent design means each new feature maps naturally to the existing pattern:

- **Quiz** → `AnalysisAgent` or new `QuizAgent`
- **Podcast** → New `MediaAgent` with TTS capability
- **Slides** → `PlanningAgent` structures content → new `ExportAgent` generates files
- **Mind Map** → `AnalysisAgent.extract()` already does entity extraction — extend to relationships

No architectural changes needed. Just new agent methods or new lightweight agents.

---

## 6. Key Design Decisions

| Decision | Rationale | Trade-off |
|---|---|---|
| **Milvus over FAISS** | Production-grade: persistence, indexing, concurrent access | Heavier dependency, requires running Milvus server |
| **Direct agent calls (not queue)** | Simpler for current scale, lower latency | Less decoupled; queue infrastructure exists for future use |
| **Celery for async processing** | Proven, scalable task queue with monitoring | Sync/async mismatch needs fixing (`asyncio.run()`) |
| **Gemini 1.5 Pro as LLM** | Strong reasoning, large context window | Vendor lock-in to Google; could abstract behind interface |
| **all-MiniLM-L6-v2 for embeddings** | Fast, lightweight, 384-dim vectors | Lower accuracy than larger models (e.g., `all-mpnet-base-v2`) |
| **S3/MinIO for file storage** | Cloud-native, scalable, presigned URL support | Requires running MinIO locally for development |
| **UUID primary keys everywhere** | No sequential ID leakage, distributed-friendly | Slightly larger indexes, less human-readable |

---

## 7. Conclusion

### Current State

InsightDocs is approximately **20% feature-complete** compared to consumer AI document tools in terms of user-facing capabilities, but **70–80% infrastructure-complete**. The hard engineering work — vector database, embedding pipeline, LLM integration, async processing, scalable storage, auth — is built.

### What's Missing (The "Last Mile")

1. **Actual document parsing** — The single biggest blocker. PDF and DOCX return placeholder strings.
2. **Output format endpoints** — Summary, quiz, slides, etc. The LLM integration exists; it just needs new prompts and routes.
3. **A frontend** — CORS is configured, API is ready. Needs a React/Vue app with drag-and-drop upload.
4. **Wiring existing code** — Summarization, entity extraction, and suggestions all work in isolation but aren't exposed as user-facing features.

### Strategic Position

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Consumer AI Tools          InsightDocs                        │
│   ─────────────────          ────────────                       │
│   Many features              Few features (currently)           │
│   Simple architecture        Sophisticated architecture         │
│   Hard to extend             Easy to extend                     │
│   Single-purpose             Platform / engine                  │
│   UI-first                   API-first                          │
│                                                                 │
│   → They ship features       → You ship infrastructure          │
│   → Adding infra is hard     → Adding features is easy          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

InsightDocs is an **engine**, not a product — yet. The agent architecture, storage layers, and LLM integration form a solid foundation. Closing the last-mile gaps (parsing, endpoints, UI) would bring it to feature parity with consumer tools while retaining a far more extensible and production-ready backend.

---

*Document generated: 2026-02-28*
*Project: InsightDocs — AI-Driven Agent Architecture for Document Intelligence*
