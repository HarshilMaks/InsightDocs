# Quick Start

This guide starts the current InsightDocs web application. It does not require or provide a command-line client.

## Prerequisites

- Docker Engine and Docker Compose
- Python 3.11+ and Node.js 20+ for local API, worker, or frontend development
- A Gemini API key for system-level generation, or a user-supplied key through Bring Your Own Key (BYOK)

Optional OCR support requires Tesseract plus the worker image or environment to provide its Python dependencies. The production API image deliberately omits the heavyweight OCR and local-model packages.

## Start the service stack

```bash
git clone https://github.com/HarshilMaks/InsightDocs.git
cd InsightDocs
cp .env.example .env
# Set the required database, Redis, Milvus/Zilliz, storage, and security values.

docker compose up -d --build
```

The Compose stack starts PostgreSQL, Redis, MinIO, the FastAPI API, and the Celery worker. The API documentation is available at `http://localhost:8000/api/v1/docs`.

## Start the frontend locally

In a separate terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite serves the frontend at `http://localhost:3000`. Configure `VITE_API_BASE_URL` for the API it should use; see [`.env.example`](../.env.example).

## Use the application

1. Register or sign in.
2. Upload a supported PDF, DOCX, PPTX, or text file (maximum 50 MB).
3. Wait until it is **Ready**. Queued, processing, and failed files cannot be selected as evidence.
4. Open a document for focused evidence chat, or create an Evidence Workspace from explicitly chosen ready documents.
5. Ask a question and inspect its answer, citations, and source highlights.
6. Use the Evidence Gate review record when a human decision or audit trail is required.

## Local development without Compose

Create and install the Python environment, then run the API and worker separately:

```bash
make venv
make install-dev
make run-backend
# In another terminal:
make run-worker
```

The local services still require reachable PostgreSQL, Redis, Milvus/Zilliz, and S3-compatible object storage. Apply migrations before using a new schema:

```bash
make migrate-up
```

## Production notes

For a memory-constrained deployment, set `EMBEDDING_MODE=sparse` consistently for both API and worker. Follow [DEPLOYMENT.md](../DEPLOYMENT.md) for the production sequence and migration gate.

## Further reading

- [Project overview](../README.md)
- [Architecture](../ARCHITECTURE.md)
- [Deployment](../DEPLOYMENT.md)
- [API reference](API.md)
