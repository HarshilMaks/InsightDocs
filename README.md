# InsightDocs

InsightDocs is an evidence-first document intelligence application for people who need to inspect the source behind an AI answer—not just receive a plausible response.

It is designed for analysts, reviewers, operators, researchers, and teams working with PDFs and business documents where traceability matters. Upload documents, select an explicit evidence corpus, ask a question, inspect the cited source regions, and review the evidence record behind the answer.

## Product positioning

| Review need | Common document, scanner, or general AI workflow | InsightDocs approach |
| --- | --- | --- |
| Turn files into searchable content | Display pages, extract text, or create a broad searchable library | Processes supported files asynchronously, then makes each document available only when it is ready. |
| Ask a question | Provide a summary or answer with little control over the evidence set | Supports a single ready document or an explicitly curated Evidence Workspace. Workspace queries never expand to the full library. |
| Check an answer | Require manual searching through the original file | Returns document, page, chunk, and spatial citation data; PDF sources can be opened with evidence highlights. |
| Keep separate investigations separate | Reuse a shared or implicit search corpus | Keeps documents, workspaces, conversations, and retrieval tenant- and owner-scoped. |
| Add human accountability | Treat the generated response as the final output | Runs Evidence Gate in shadow mode and retains an auditable claim-support record for human review. |
| Operate within limited infrastructure | Assume local dense models and high-memory services | Supports deterministic sparse retrieval for constrained deployments while retaining the same evidence workflow. |

The comparison describes workflow design, not a claim about every third-party product. InsightDocs is most valuable when evidence scope, source inspection, and review traceability matter more than producing an ungrounded answer quickly.

## Who it is for

| User | Typical use | How InsightDocs helps |
| --- | --- | --- |
| Analysts and researchers | Investigate reports, policies, submissions, or reference packs | Build a bounded corpus, ask focused questions, and inspect supporting source regions. |
| Review and risk teams | Prepare a human decision from retained evidence | Use Evidence Gate records and the owner-scoped review queue without treating automation as final approval. |
| Operations and program teams | Answer recurring questions from controlled business documents | Keep each topic in a private workspace and reopen its saved conversation history. |
| Technical teams | Operate an evidence-aware document application | Deploy the API, worker, storage, database, and retrieval services with documented sparse-mode support. |

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
