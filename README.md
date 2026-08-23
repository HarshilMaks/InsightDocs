# InsightDocs

InsightDocs is an evidence-first document intelligence application for work that must remain traceable to selected source material. It is built for analysts, reviewers, operators, researchers, and teams working with PDFs and business documents where a plausible answer is not enough.

## Not a generic document chat

Broad notebook-style research tools and general-purpose chat assistants are useful for open-ended exploration, drafting, and asking questions across a library. InsightDocs is for a different moment in the workflow: when a user must define the evidence set, inspect where an answer came from, and retain a reviewable record of the result.

| Broad notebook or chat workflow | InsightDocs workflow |
| --- | --- |
| Put material in a broad notebook or library, then explore it conversationally | Select one ready document or create a named private Evidence Workspace for a specific investigation. |
| Treat the available library as conversational context | Enforce the selected ready-document set as a retrieval boundary. A workspace query never expands to the full library. |
| Receive a useful answer, summary, or synthesis | Receive an answer with document, page, chunk, and spatial source references that can be inspected in the original PDF. |
| Use citations as helpful reading references | Preserve exact PDF regions for new ingestions so evidence highlights can point to separated source passages rather than only a broad page area. |
| Continue an open chat thread | Reopen saved document or workspace conversations with their original evidence scope. |
| Hand the generated answer to a person for informal review | Retain a shadow-mode Evidence Gate claim-support record and owner-scoped review decisions for human accountability. |

Use a general notebook or chat tool when the goal is broad exploration or drafting. Use InsightDocs when the answer must stay tied to a controlled corpus and a reviewer needs to inspect the evidence behind it.

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

## Run locally (optional)

Local setup is for development or evaluation. It does not deploy or publish the application.

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL, Redis, Milvus or Zilliz, and S3-compatible storage
- A Gemini API key, either platform-configured or supplied through BYOK

### Service stack

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
cp .env.example .env
# Fill in required service credentials in .env

docker compose up -d --build
```

This starts the backend service stack. The API is available at `http://localhost:8000` and its generated documentation is at `http://localhost:8000/api/v1/docs`. To run the frontend locally, follow [frontend/README.md](frontend/README.md).

### Migrations

`alembic upgrade head` is not a deployment command by itself. It applies database schema changes.

- For a new local database, or after pulling a release that includes a new migration, run:

  ```bash
  docker compose exec api alembic upgrade head
  ```

- If the local database is already at the current revision, no migration action is needed.
- In production, `scripts/start_api.sh` runs `alembic upgrade head` before the API starts and fails closed if it cannot succeed. Follow [DEPLOYMENT.md](DEPLOYMENT.md) rather than running ad hoc production commands.

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
