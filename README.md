# InsightDocs

InsightDocs is an evidence-first document intelligence application for people who need to inspect the source behind an AI answer—not just receive a plausible response.

It is designed for analysts, reviewers, operators, researchers, and teams working with PDFs and business documents where traceability matters. Upload documents, select an explicit evidence corpus, ask a question, inspect the cited source regions, and review the evidence record behind the answer.

## What it does

- Ingests PDF, DOCX, PPTX, and text documents through S3-compatible storage and Celery workers.
- Provides single-document evidence chat and private multi-document Evidence Workspaces.
- Restricts workspace retrieval to explicitly selected, ready documents; it never silently falls back to the full library.
- Returns source citations with document, page, chunk, and spatial coordinates.
- Renders PDF evidence highlights. New PDF ingestions preserve separated line regions for tighter highlights; older documents use their stored single-region fallback until re-ingested.
- Runs Evidence Gate in shadow mode, retaining an immutable audit record and claim-support results without blocking the answer.
- Provides an owner-scoped review queue with append-only accept/reject history and optimistic concurrency protection.
- Supports encrypted Bring Your Own Key Gemini access and tenant-scoped relational and vector retrieval.
- Supports sparse retrieval mode for constrained deployments without loading local PyTorch or SentenceTransformers models.

## Product flow

```text
Upload document
  → worker parses, chunks, indexes, and marks it ready
  → choose one document or create an Evidence Workspace
  → ask a question
  → inspect answer, sources, and page-level highlights
  → review the Evidence Gate record when human approval is needed
```

Only documents marked **Ready** are available for evidence queries. Queued, processing, and failed documents remain visible but cannot be selected as evidence.

## Architecture

```text
React + TypeScript (Vite)
  → FastAPI API
  → PostgreSQL: users, documents, chunks, history, audits, reviews
  → Milvus/Zilliz: tenant-scoped vector retrieval
  → Redis + Celery worker: asynchronous document processing
  → S3-compatible object storage: original documents
  → Gemini: answer generation and evidence checks
```

For the production design and operational boundaries, see [ARCHITECTURE.md](ARCHITECTURE.md). For deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL, Redis, Milvus or Zilliz, and S3-compatible storage
- A Gemini API key, either platform-configured or supplied through BYOK

### Local setup

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
cp .env.example .env
# Fill in required service credentials in .env

docker-compose up -d --build
```

The API is available at `http://localhost:8000` and API documentation at `http://localhost:8000/api/v1/docs`.

For a production-safe Render and Vercel deployment, follow [DEPLOYMENT.md](DEPLOYMENT.md). Apply migrations before serving a new release:

```bash
alembic upgrade head
```

## Configuration

Production deployments with approximately 512 MB of memory must set:

```text
EMBEDDING_MODE=sparse
```

Sparse mode uses deterministic hashed sparse vectors and avoids local dense embedding, reranking, and PyTorch model startup. The API and worker must use the same retrieval configuration.

Gemini model availability differs by key. The configured model chain starts with `gemini-3.6-flash`, then `gemini-3-flash-preview`, and dynamically discovers an accessible text-generation model if required.

## Validation

```bash
# Backend tests
.venv/bin/python -m pytest -q tests/

# Frontend type-check and production build
cd frontend && npm run build

# PostgreSQL migration SQL preview
DATABASE_URL='postgresql://user:password@localhost:5432/insightdocs' \
  .venv/bin/alembic upgrade head --sql
```

The focused release regressions cover citation geometry, Evidence Gate review decisions, workspace ownership and strict retrieval scope, ready-document enforcement, history isolation and ordering, Gemini fallback, and request cancellation handling.

## Current boundaries

InsightDocs is a document-evidence product, not an automated truth system. A citation or Evidence Gate result means a claim was assessed against retained selected evidence; it does not establish universal truth. Human review remains the final decision point.

The current release does not provide organization-wide sharing/RBAC, external data connectors, document change monitoring, comparison/conflict matrices, draft-claim verification, or evidence-packet export.

## License

Apache License 2.0. See [LICENSE](LICENSE).
