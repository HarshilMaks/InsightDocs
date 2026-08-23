# InsightDocs Architecture

InsightDocs is an evidence-first document application. Its architecture favors explicit retrieval scope, inspectable citations, owner isolation, and operational safety over open-ended autonomous behavior.

## Runtime topology

```mermaid
flowchart TB
    Browser[React and TypeScript client] -->|HTTPS| API[FastAPI API]
    API --> DB[(PostgreSQL: application data)]
    API --> V[(Milvus or Zilliz: vectors)]
    API --> S[(S3-compatible storage: originals)]
    API --> G[Gemini: answers and checks]
    API --> R[(Redis)]
    R --> W[Celery worker: processing and indexing]
    W --> S
    W --> DB
    W --> V
```

| Component | Responsibility |
| --- | --- |
| Browser client | Authentication UI, document library, Evidence Workspaces, source viewing, history, and review actions. |
| FastAPI API | Authentication, ownership checks, upload handoff, query orchestration, history, Evidence Gate persistence, and review APIs. |
| Celery worker | Parsing, OCR where configured, chunking, embedding, vector indexing, and document state transitions. |
| PostgreSQL | Application records, document/chunk metadata, query history, audit runs, and append-only review decisions. |
| Milvus or Zilliz | Retrieval vectors constrained by tenant and document scope. |
| S3-compatible storage | Original uploaded files. The API issues short-lived owner-checked URLs for viewing. |
| Redis | Celery broker/result backend and rate-limit storage. |

A user may provide an encrypted BYOK Gemini key. A configured system key is an optional fallback. Gemini is never the source of record for ownership, document state, citations, or review decisions.

## Ingestion lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant S as Object storage
    participant Q as Redis and Celery
    participant W as Worker
    participant DB as PostgreSQL
    participant V as Vector store

    U->>A: Upload supported file
    A->>S: Store original object
    A->>DB: Create pending document
    A->>Q: Queue processing task
    Q->>W: Deliver task
    W->>S: Download its own temporary copy
    W->>W: Extract text, tables, and PDF geometry
    W->>DB: Store chunks and metadata
    W->>V: Index tenant and document-scoped vectors
    W->>DB: Mark document completed
```

The upload API stores the original file before it queues the worker. A worker downloads its own temporary copy, so processing does not depend on an API container’s local filesystem.

A document becomes queryable only after processing succeeds. The UI calls this **Ready**; the persisted state is `completed`. Queued, processing, and failed documents remain unavailable as evidence.

## Query and evidence lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant DB as PostgreSQL
    participant V as Vector store
    participant G as Gemini

    U->>A: Ask against document or workspace
    A->>DB: Verify owner and ready-document scope
    A->>V: Retrieve only allowed tenant/document vectors
    V-->>A: Candidate chunks
    A->>DB: Hydrate citation metadata and source geometry
    A->>G: Generate from retrieved source context
    G-->>A: Answer and claim assessment
    A->>DB: Persist query, source snapshot, and shadow audit
    A-->>U: Answer, citations, and audit summary
```

### Scope rules

- Every vector search is constrained by `user_id`.
- A single-document query validates ownership and adds that `document_id` to retrieval.
- A workspace query resolves the owner’s explicitly selected completed documents and passes a document allow-list.
- An empty workspace, or one without ready documents, returns an error. It never falls back to the user’s full library.
- A conversation ID cannot be reused across different workspaces.

### Cancellation

The browser may cancel an in-flight request. The API checks for a disconnected client after generation and before persistence. When a disconnect is observed, it returns `499` and does not save the query or Evidence Gate record. Gemini generation is non-streaming, so cancellation cannot revoke a request already sent to the provider.

## Citations and source inspection

Retrieved vector results are hydrated from PostgreSQL before they are returned. A source reference carries document, page, chunk, section, similarity score, and spatial geometry when available.

| Source type | Citation behavior |
| --- | --- |
| New text-based PDF ingestion | Stores separated line/region boxes. The viewer renders one overlay per region. |
| Legacy PDF ingestion | Retains the stored single bounding box. Re-ingest for multi-region geometry. |
| Scanned or OCR-only document | Can provide text evidence, but may not have spatial PDF highlights. |

## Evidence Gate and review

```mermaid
flowchart LR
    Q[Persisted query and source snapshot] --> G[Evidence Gate shadow audit]
    G --> C[Claim support outcomes]
    G --> H[Immutable audit hashes]
    C --> R[Owner review queue]
    H --> R
    R --> D[Append-only accept or reject decision]
```

Evidence Gate is a shadow-mode assessment. It records whether answer claims are supported by the selected source snapshot when verification is available. It does not block the answer, search the web, declare universal truth, or make a decision for the user.

Review decisions are owner-scoped and append-only. A compare-and-swap `review_version` prevents a stale accept/reject action from silently overwriting another decision.

## Security and ownership boundaries

| Boundary | Enforcement |
| --- | --- |
| Authentication | JWT-protected user data routes. |
| Document access | Owner filter on document, workspace membership, history, audit, review, and presigned file URL operations. |
| Retrieval | Tenant filter plus direct-document or workspace allow-list. |
| BYOK | Encrypted at rest; decrypted only for an authorized request; never returned through the API. |
| Storage access | Presigned original-file URLs are issued only after ownership checks and expire quickly. |
| Browser origin | Explicit allowed-origin configuration. |

## Deployment boundary

API and worker are separate services. They must share compatible PostgreSQL, Redis, storage, vector, encryption, and retrieval-mode configuration. In constrained deployments, `EMBEDDING_MODE=sparse` avoids importing local dense embedding, reranking, and PyTorch models.

`scripts/start_api.sh` runs `alembic upgrade head` before Uvicorn starts. A migration failure stops the API; a schema-mismatched service must not report itself healthy.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the release topology, configuration placement, and verification procedure.
