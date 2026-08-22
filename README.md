# InsightDocs

> An enterprise document intelligence platform that lets you ask questions about your documents and get answers backed by **precise, verifiable evidence** — not vague citations.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## What Makes This Different

Most RAG systems say "Source: document.pdf" and leave you guessing. InsightDocs shows you the **exact page, paragraph, and pixel region** the answer came from — and **verifies each claim** against the evidence before showing it to you.

**The signature interaction:** Ask a question → get an answer → click a sentence → the PDF jumps to and highlights the exact supporting region.

## Core Capabilities

- **Pixel-level citation grounding** — bounding-box coordinates for every retrieved chunk, rendered as a live highlight overlay on the source PDF
- **Per-claim verification** — each factual sentence in the answer is independently classified as "supported" or "unsupported" against the retrieved evidence
- **Section-aware, table-atomic chunking** — headings detected via font-size heuristics, tables kept as atomic units (never split), parent-child chunk hierarchy for precise retrieval + broad LLM context
- **Hybrid retrieval** — Milvus dense + sparse vector search with cross-encoder reranking and document-scoped filtering
- **BYOK (Bring Your Own Key)** — user-provided Gemini API keys encrypted with AES-256 (Fernet + PBKDF2HMAC, per-user salt)
- **Tenant isolation** — user-scoped filtering enforced at both the relational DB and vector DB layers
- **Evaluation harness** — golden dataset + CI-runnable metrics (Answer Grounding Rate, Source Recall@K, Citation Coverage)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React/TypeScript Frontend (Vite)                           │
│  PDF Viewer + Citation Highlighting + Claim Verification UI │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                            │
│  Upload → S3 → Celery Worker → Parse → Chunk → Embed       │
│  Query → Hybrid Search → Rerank → Generate → Verify        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL │ Milvus (Vectors) │ Redis (Queue) │ S3/MinIO   │
└─────────────────────────────────────────────────────────────┘
```

### Query Pipeline

```
Query → Document Scope Check → Dense+Sparse Hybrid Search (Milvus)
      → Cross-Encoder Reranking → Citation Hydration (PostgreSQL)
      → LLM Generation (Gemini) → Per-Claim Verification
      → Structured Response with Confidence Badges
```

### Ingestion Pipeline

```
Upload → S3/MinIO (API uploads directly, never passes local paths to workers)
       → Celery Worker downloads own temp copy
       → Parse (PDF/DOCX/PPTX/TXT, OCR for scanned docs)
       → Section-aware chunking (heading detection, table atomicity, parent-child)
       → Dense + Sparse embedding → Milvus (with user_id + document_id)
       → PostgreSQL chunk persistence (with bbox, section_title, parent linkage)
       → Summary generation → Complete
```

## Quick Start

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
cp .env.example .env  # Edit and add your GEMINI_API_KEY
docker-compose up -d
```

Services:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs
- **MinIO Console**: http://localhost:9001

## Evaluation

```bash
# Run evaluation harness (mock mode, no services needed):
python eval/run_eval.py --mode mock

# Against a live backend:
python eval/run_eval.py --mode live --token <jwt_token>
```

Metrics produced: Answer Grounding Rate, Source Recall@K, Citation Coverage.
Exit code 1 if any metric falls below configurable thresholds (CI gate).

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic, SQLAlchemy |
| Workers | Celery, Redis |
| Database | PostgreSQL |
| Vectors | Milvus (hybrid dense + sparse) |
| Storage | S3/MinIO |
| LLM | Google Gemini (BYOK) |
| Embeddings | Sentence Transformers (BAAI/bge-base-en-v1.5) |
| Reranking | Cross-Encoder (ms-marco-MiniLM-L-6-v2) |
| Frontend | React, TypeScript, Vite, Tailwind, react-pdf |
| Auth | JWT (python-jose, bcrypt) |
| Logging | Structured JSON (production) / plain text (dev) |

## Project Structure

```
InsightDocs/
├── backend/
│   ├── agents/          # Orchestrator + DataAgent + AnalysisAgent
│   ├── api/             # FastAPI routes (documents, query, auth, users, tasks)
│   ├── core/            # Security, rate limiting, logging, base agent
│   ├── middleware/      # Input/output guardrails, claim verification
│   ├── models/          # SQLAlchemy models, Alembic migrations
│   ├── storage/         # S3/MinIO file storage
│   ├── utils/           # LLM client, embeddings, document processor, reranker, OCR
│   └── workers/         # Celery tasks
├── frontend/
│   └── src/
│       ├── components/  # PdfViewer, ChatPanel, CitationsPanel, etc.
│       ├── pages/       # DocumentPage, DashboardPage, SettingsPage
│       └── lib/         # API client, types, utilities
├── eval/                # Golden dataset + evaluation harness
├── tests/               # Unit + integration tests (125+ passing)
├── alembic/             # Database migrations
└── .lock/               # Project vision & roadmap (local planning, gitignored)
```

## Testing

```bash
# Full suite:
pytest tests/

# Current state: 125+ passing, 14 pre-existing env-gap failures
# (missing optional native deps: sentence-transformers, LibreOffice, ImageMagick)
```

## Development Status

### Completed (Verified with tests + static analysis)
- ✅ Reliable ingestion pipeline (S3-first upload, worker temp-file cleanup)
- ✅ Section-aware, table-atomic, parent-child chunking with heading detection
- ✅ Interactive PDF viewer with citation bbox highlighting
- ✅ Per-claim verification (supported/unsupported per sentence)
- ✅ Evaluation harness with CI-gate thresholds
- ✅ Structured JSON logging (production) / plain text (development)
- ✅ Document-scoped querying (workspace-level retrieval filtering)
- ✅ BYOK API key encryption + tenant-isolated vector search
- ✅ Cross-encoder reranking

### Planned (Not yet implemented)
- ⬜ Knowledge Graph (Neo4j entity extraction + graph-enhanced retrieval)
- ⬜ RBAC / Organizations / Document sharing
- ⬜ OpenTelemetry distributed tracing
- ⬜ Token usage accounting / cost dashboard

## License

Apache License 2.0 — see [LICENSE](LICENSE).


## Evidence Gate and Review Queue

InsightDocs now includes an additive **Evidence Gate** for document-grounded answers. In
its current **shadow mode**, every eligible query can create an immutable audit record
that binds the generated candidate, delivered answer, policy version, and source
snapshot by hash. It classifies the run as `passed`, `failed`, `degraded`, or
`abstained` without blocking a user answer.

The protected **Reviews** area gives a document owner a queue of audit runs, claim-level
support status, the retained source quote/page/bbox metadata, and an append-only
accepted/rejected review decision history. Review decisions use optimistic concurrency:
a stale decision is rejected rather than silently overwriting another review.

This is not a claim that a citation is universally true. It means the claim was or was
not supported by the selected, inspectable source evidence. The review queue is a human
verification workflow, not an automated truth guarantee.

Before using this capability against any database, apply the two forward migrations:

```bash
alembic upgrade head
```

The Evidence Gate starts in shadow mode only. It does not replace the existing Document
Workspace, query request contract, or source viewer.
