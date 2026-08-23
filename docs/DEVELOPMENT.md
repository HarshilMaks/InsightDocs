# Development Guide

## Scope

InsightDocs is a React/Vite frontend with a FastAPI API, Celery worker, PostgreSQL, Redis, Milvus or Zilliz, S3-compatible storage, and Gemini-backed generation. The API handles authenticated requests; the worker performs asynchronous document parsing, chunking, and indexing.

For product behavior and production boundaries, read [README.md](../README.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) first.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Engine and Docker Compose for the local service stack
- `uv` for the Makefile-managed Python installation commands

## Setup

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
cp .env.example .env
make venv
make install-dev
```

Set the required service configuration in `.env`. The file is intentionally ignored by Git; do not place credentials in source files, tests, Markdown, or commits.

## Run locally

Start infrastructure and the service containers:

```bash
docker compose up -d --build
```

Or use local API and worker processes with reachable infrastructure:

```bash
make run-backend
# In a separate terminal:
make run-worker
```

Start the frontend in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The API documentation is served at `http://localhost:8000/api/v1/docs` and the Vite frontend is served at `http://localhost:3000`.

## Validation

Run the full backend suite and frontend production build before submitting a change:

```bash
.venv/bin/python -m pytest -q tests/
(cd frontend && npm run build)
```

Validate migration generation without connecting to a database server:

```bash
DATABASE_URL='postgresql://user:password@localhost:5432/insightdocs' \
  .venv/bin/alembic upgrade head --sql
```

`make lint` runs Python syntax compilation and the frontend TypeScript check. It is a fast code check, not a substitute for the full backend test suite and frontend production build above.

## Database changes

1. Update the SQLAlchemy models in `backend/models/schemas.py`.
2. Generate an Alembic revision with `make migrate-generate`.
3. Review the migration file and generated SQL.
4. Apply it locally with `make migrate-up`.
5. Include the migration in the same change as the model update.

Production migrations are a release gate: `scripts/start_api.sh` exits instead of starting the API when `alembic upgrade head` fails. Do not use `alembic stamp` or delete `alembic_version` to bypass a migration/source mismatch.

## Contribution boundaries

- Keep workspace retrieval restricted to its explicit ready-document membership.
- Preserve tenant and owner checks in relational, vector, history, audit, and review operations.
- Preserve the API/worker retrieval configuration match, especially `EMBEDDING_MODE`.
- Treat Evidence Gate as a retained assessment for human review, not an automated truth decision.
- Add targeted regressions for behavior changes; do not modify tests merely to hide a regression.
