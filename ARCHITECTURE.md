# InsightDocs Architecture

## Purpose

InsightDocs turns uploaded documents into reviewable evidence. The design prioritizes provenance, tenant isolation, explicit retrieval scope, and operational safety over open-ended autonomous behavior.

## Runtime components

```text
Browser
  React + TypeScript + Vite
       │ HTTPS
FastAPI API
  auth, library, workspaces, query history, Evidence Gate, review queue
       │                    │
PostgreSQL                 Milvus / Zilliz
  application state         tenant-scoped vector records
       │                    │
Redis + Celery worker ──────┘
  asynchronous parsing, chunking, embedding
       │
S3-compatible storage
  original uploaded files
```

Gemini is used for answer generation and optional safety/evidence checks. A user can supply an encrypted BYOK key; a configured system key is an optional fallback.

## Document lifecycle

1. The API validates an upload and writes the original file to object storage.
2. It creates a pending document and queues a Celery task.
3. The worker downloads its own temporary copy, extracts text, tables, and PDF geometry where available, then creates structural chunks.
4. The worker writes chunks to PostgreSQL and their vectors to Milvus with both `user_id` and `document_id` metadata.
5. The document becomes `completed` only after processing succeeds. Only completed documents are eligible for evidence queries.

The API never treats a queued, processing, or failed document as searchable evidence. The UI reflects the same rule.

## Retrieval and evidence scope

Every vector search is tenant-scoped by `user_id`.

- A single-document query adds a verified `document_id` filter.
- A workspace query resolves the owner’s selected, completed documents and sends an explicit `document_id in [...]` allow-list.
- An empty workspace or workspace with no ready documents returns an error. It does not fall back to the user’s whole library.

Production constrained to approximately 512 MB should run with `EMBEDDING_MODE=sparse`. Sparse mode uses deterministic hashed sparse vectors and avoids importing SentenceTransformers, BGEM3, cross-encoders, and PyTorch. Hybrid retrieval remains a development/deployment option only when the required model capacity is available.

## Citations and PDF highlights

Retrieved vector records are hydrated from PostgreSQL before an answer is returned. A source reference includes its document, page, chunk, section, similarity score, and spatial geometry when available.

New text-based PDF ingestions store separated line/region boxes. The frontend renders one overlay per region so the cited evidence is not represented by a broad page rectangle. Legacy chunks retain their stored single bbox and remain compatible; re-ingest a document to obtain multi-region geometry. Scanned/OCR-only documents can provide text evidence without spatial highlights.

## Query, history, and cancellation

A completed query persists the question, answer, sources, conversation ID, timing, and optional workspace provenance. History is owner-scoped and can reopen a routed document or workspace conversation when provenance exists.

The browser can cancel an in-flight query. The API checks for a disconnected client after generation and before persistence; when detected, it does not create a query history or Evidence Gate record. Gemini generation is non-streaming, so a cancellation cannot guarantee revocation of an already-issued provider request.

## Evidence Gate and review

Evidence Gate runs in shadow mode. It creates an immutable audit run with the answer and source snapshot hashes, along with claim-support outcomes when verification is available. It does not block answer delivery.

Review decisions are owner-scoped and append-only. They use a `review_version` compare-and-swap update, so stale accept/reject actions return a conflict instead of overwriting another decision.

## Security boundaries

- JWT authentication is required for user data.
- Documents, workspaces, history, vectors, reviews, and presigned file URLs are owner-scoped.
- BYOK values are encrypted at rest and decrypted only for an authorized request.
- Presigned object-storage URLs are issued only after document ownership is verified.
- CORS is configured from an explicit allowed-origin list.

## Deployment boundaries

The API and worker are deployed separately. They must share database, Redis, object-storage, Milvus, encryption key, and retrieval-mode configuration. The API applies Alembic migrations before startup and fails the deployment if migration fails; a service with a schema mismatch must not report itself as healthy.

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment and verification steps.
