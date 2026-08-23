<p align="center">
  <img src="frontend/brand/insightdocs-logo.png" alt="InsightDocs logo" width="132" />
</p>

<h1 align="center">InsightDocs</h1>

<p align="center"><strong>Controlled evidence review for documents.</strong></p>

<p align="center">
  <a href="#how-it-works">How it works</a> ·
  <a href="#why-it-is-different">Why it is different</a> ·
  <a href="ARCHITECTURE.md">Architecture</a> ·
  <a href="DEPLOYMENT.md">Deployment</a> ·
  <a href="PROJECT_STATUS.md">Project status</a>
</p>

InsightDocs is for work that must remain traceable to selected source material. It gives a reviewer a bounded evidence set, an answer grounded in that set, and the source context needed to inspect that answer before relying on it.

## How it works

```mermaid
flowchart LR
    U[Upload a source] --> P[Worker processes it]
    P -->|Ready| L[Evidence library]
    L --> D[One document]
    L --> W[Evidence Workspace]
    D --> Q[Ask a question]
    W --> Q
    Q --> C[Inspect citations and PDF regions]
    Q --> G[Evidence Gate audit]
    G --> R[Human review decision]
```

1. Upload a PDF, DOCX, PPTX, or text file. Processing extracts, chunks, and indexes it in the background.
2. Wait until the document is **Ready**. Queued, processing, and failed documents cannot be used as evidence.
3. Ask against one ready document or a named private Evidence Workspace containing explicitly selected ready documents.
4. Inspect the answer, source document, page, chunk, and PDF highlight. If review is needed, open the retained Evidence Gate record.

## Why it is different

NotebookLM, ChatGPT, and similar tools are useful for exploring a collection, developing an understanding, and drafting. InsightDocs is for the point after exploration, when a person needs to answer from a controlled corpus and show the source behind the answer.

| When the work looks like this | Broad notebook or chat workflow | InsightDocs |
| --- | --- | --- |
| I am exploring a changing collection | Keep a broad notebook or library open | Create a named Evidence Workspace for one investigation. |
| I need the answer constrained to chosen files | The available library is conversational context | Workspace membership is an enforced retrieval allow-list; it never falls back to the rest of the library. |
| I need to inspect the answer myself | Read a citation or search the source again | Open the original PDF at the cited page, chunk, and stored source region. |
| I need to return to the work later | Continue a general chat | Reopen saved document or workspace conversations with their original evidence scope. |
| A person must decide what to do next | Hand over the generated answer | Retain an Evidence Gate claim-support record and append-only review decisions. |

InsightDocs is not trying to be a larger general chat window. It is a controlled review environment for decisions where scope, source inspection, and durable evidence records matter.

## What the product protects

| Boundary | Product behavior |
| --- | --- |
| **Scope** | A workspace query uses only its selected ready documents. |
| **Ownership** | Documents, workspaces, history, citations, audits, and reviews are owner-scoped. |
| **Source context** | Citations carry document, page, chunk, and spatial information. New PDF ingestions preserve separated source regions. |
| **Human decision** | Evidence Gate runs in shadow mode. It records an assessment; it does not declare truth or make the final decision. |
| **Operational safety** | API startup fails closed if database migrations cannot complete. Sparse retrieval supports memory-constrained deployments. |

## Runtime at a glance

```mermaid
flowchart TB
    B[React and TypeScript client] --> A[FastAPI API]
    A --> DB[(PostgreSQL)]
    A --> V[(Milvus or Zilliz)]
    A --> S[(S3-compatible storage)]
    A --> G[Gemini]
    A --> R[(Redis)]
    R --> W[Celery worker]
    W --> S
    W --> DB
    W --> V
```

The API handles authentication, ownership checks, workspaces, queries, history, audits, and reviews. The worker handles asynchronous parsing, OCR where configured, chunking, and indexing. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full ingestion and query flows.

## Research context

InsightDocs is informed by work on retrieval-grounded generation and citation quality. These papers motivate design choices; they do not validate, certify, or prove the correctness of this product.

- Lewis et al., [*Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*](https://arxiv.org/abs/2005.11401), 2020: retrieval can ground generation in an explicit external knowledge source.
- Gao et al., [*Enabling Large Language Models to Generate Text with Citations*](https://arxiv.org/abs/2305.14627), 2023: citation quality is a distinct property that needs to be evaluated alongside answer quality.

## Who uses it

| User | Typical use |
| --- | --- |
| Analysts and researchers | Investigate reports, policies, submissions, or reference packs. |
| Review and risk teams | Prepare a human decision from retained evidence and claim-support records. |
| Operations teams | Keep recurring business-document work separated into private workspaces. |
| Technical teams | Operate an evidence-aware application with explicit retrieval and deployment boundaries. |

## Documentation map

| If you need to… | Read |
| --- | --- |
| Understand components, data flow, citations, and ownership boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Deploy API, worker, storage, vector search, and frontend | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Configure environment variables | [.env.example](.env.example) |
| Use the verified public API surface | [docs/API.md](docs/API.md) and `/api/v1/docs` |
| Run locally | [docs/QUICKSTART.md](docs/QUICKSTART.md) |
| Develop and validate changes | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Check supported scope and maintainership rules | [PROJECT_STATUS.md](PROJECT_STATUS.md) |

## Run locally (optional)

Local setup is for development or evaluation. It does not deploy or publish the application.

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
cp .env.example .env
# Fill in required service credentials in .env

docker compose up -d --build
```

The backend API is available at `http://localhost:8000`, and generated API documentation is at `http://localhost:8000/api/v1/docs`. To run the frontend locally, follow [frontend/README.md](frontend/README.md).

### Database migrations

`alembic upgrade head` applies schema changes; it is not a deployment command by itself.

- For a new local database, or after pulling a release with a new migration:

  ```bash
  docker compose exec api alembic upgrade head
  ```

- If the local database is already current, no action is required.
- Production API startup runs migrations before serving and fails closed on failure. Follow [DEPLOYMENT.md](DEPLOYMENT.md) instead of running ad hoc production commands.

## Deployment configuration

A 512 MB API or worker deployment must use:

```text
EMBEDDING_MODE=sparse
```

Sparse mode avoids local PyTorch, SentenceTransformers, and reranking model startup. API and worker must use compatible retrieval configuration. Gemini model availability differs by key; the configured chain starts with `gemini-3.6-flash`, then `gemini-3-flash-preview`, and can discover an accessible text-generation model when needed.

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

## Current boundaries

InsightDocs is a document-evidence product, not an automated truth system. The current release does not provide organization-wide sharing/RBAC, external data connectors, document change monitoring, comparison/conflict matrices, draft-claim verification, external corroboration, or evidence-packet export.

## License

Apache License 2.0. See [LICENSE](LICENSE).
