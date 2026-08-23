# System Overview

## Purpose

InsightDocs is an evidence-first document intelligence application. It helps a user work from an explicitly bounded document corpus, inspect the source behind an answer, and retain a reviewable evidence record. It is not an automated truth or approval system.

## Runtime components

```text
React + TypeScript (Vite)
  -> FastAPI API
  -> PostgreSQL: users, documents, chunks, history, audits, reviews
  -> Milvus/Zilliz: tenant-scoped vector retrieval
  -> Redis + Celery worker: asynchronous processing
  -> S3-compatible storage: original documents
  -> Gemini: answer generation and evidence checks
```

The API owns authentication, authorization, queries, history, Evidence Workspaces, and Evidence Gate review APIs. The worker owns the expensive parsing, OCR where configured, chunking, embedding, and indexing work.

## Document lifecycle

1. An authenticated user uploads a supported PDF, DOCX, PPTX, or text file.
2. The API stores the original object and queues a Celery task.
3. The worker extracts text, preserves available PDF spatial information, chunks the content, and indexes it.
4. The document becomes ready only after processing succeeds.
5. Only ready documents can be queried directly or added as usable evidence in a workspace.

The product UI may present the completed processing state as **Ready**. Pending, processing, and failed documents remain unavailable for evidence queries.

## Evidence workflow

A user can ask against one ready document or an Evidence Workspace. A workspace is a private, explicit corpus: the query service resolves only its selected ready documents and does not silently search the broader library.

Answers include source references. For PDFs, new ingestions retain multiple precise source regions; documents ingested before that capability retain their original single-region geometry until re-ingested.

Evidence Gate runs after answer generation in shadow mode. It stores an audit and claim-support assessment but does not block the answer. Users can review owner-scoped records and append accept/reject decisions with optimistic concurrency protection.

## Security and ownership

- Routes require authenticated users except health and registration/login flows.
- Documents, workspaces, query history, audits, and reviews are scoped to their owner.
- Retrieval carries tenant constraints and workspace document allow-lists.
- Uploaded originals remain in S3-compatible storage; the API issues a short-lived owner-checked file URL for viewing.
- BYOK Gemini credentials are stored encrypted and are never returned in API responses.

## Deployment boundary

The API and worker must use compatible configuration. On constrained hosts, `EMBEDDING_MODE=sparse` avoids loading local dense embedding and reranking models. Startup runs Alembic migrations as a fail-closed release gate; an API process does not serve if its schema upgrade fails.

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the complete design and [DEPLOYMENT.md](../DEPLOYMENT.md) for the release procedure.
