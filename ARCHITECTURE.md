# InsightDocs Architecture Guide

## System Overview

InsightDocs is a multi-agent RAG system built with 5 distinct layers that work together to transform documents into queryable intelligence.

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  FastAPI REST API  │  CLI Tool  │  Swagger UI Documentation │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     AGENT SYSTEM LAYER                      │
│  Orchestrator ──→ DataAgent ──→ AnalysisAgent ──→ Planning │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   ASYNC WORKERS LAYER                       │
│  Celery Workers: process_document, generate_embeddings     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   DATA STORAGE LAYER                        │
│  PostgreSQL │ Milvus Vector DB │ Redis │ S3/MinIO Storage  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  LLM INTEGRATION LAYER                      │
│  Gemini API Client  │  SentenceTransformers Embeddings    │
└─────────────────────────────────────────────────────────────┘
```

## Code Structure

All application code lives in the `backend/` directory:

```
backend/
├── agents/           # Multi-agent system
├── api/             # FastAPI endpoints  
├── core/            # Base classes and utilities
├── models/          # Database schemas
├── utils/           # LLM, embeddings, document processing
├── workers/         # Celery background tasks
└── storage/         # File storage integration
```

## Layer Details

### 1. Presentation Layer

**FastAPI REST API**
- Document upload/management endpoints
- RAG query interface
- Task status monitoring
- JWT authentication (Enforced)

**CLI Tool**
- Direct system interaction
- Development and testing utilities

**Swagger UI**
- Auto-generated API documentation
- Interactive endpoint testing

### 2. Agent System Layer

All agents inherit from `BaseAgent` with async `process(message)` interface:

```
BaseAgent
├── async process(message) → AgentResponse
├── logger: Logger
└── agent_id: str

┌─────────────────────────────────────────────────────────────┐
│                    AGENT WORKFLOW                           │
│                                                             │
│  Orchestrator ──┐                                          │
│                 │                                          │
│                 ├──→ DataAgent                             │
│                 │    ├── ingest_document()                 │
│                 │    ├── transform_content()               │
│                 │    └── store_chunks()                    │
│                 │                                          │
│                 ├──→ AnalysisAgent                         │
│                 │    ├── generate_embeddings()             │
│                 │    ├── summarize_document()              │
│                 │    └── extract_entities()                │
│                 │                                          │
│                 └──→ PlanningAgent                         │
│                      ├── suggest_actions()                 │
│                      ├── track_progress()                  │
│                      └── make_decisions()                  │
└─────────────────────────────────────────────────────────────┘
```

**Orchestrator Agent**
- Coordinates all other agents
- Manages workflow execution
- Direct agent invocation (not via MessageQueue)

**DataAgent**
- Document ingestion and parsing
- Content transformation and chunking
- Database storage operations

**AnalysisAgent** 
- Vector embedding generation
- Document summarization
- Entity extraction

**PlanningAgent**
- Workflow planning and suggestions
- Progress tracking
- Decision support

### 3. Async Workers Layer

**Celery Configuration**
- Redis as message broker
- Background task processing
- Uses `asyncio.run()` wrapper for async operations
- **Security**: Workers operate with scoped DB sessions and require explicit `user_id` ownership for all tasks.

**Core Tasks**
- `process_document`: Full document processing pipeline (Ingest -> Chunk -> Embed -> Summarize)
- `generate_embeddings`: Vector generation for chunks
- `cleanup_old_tasks`: Maintenance operations

### 4. Data Storage Layer

**PostgreSQL Schema**
```sql
-- All tables use UUID primary keys with TimestampMixin
users: id, email, hashed_password, is_active, created_at, updated_at
documents: id, user_id, filename, file_path, status, summary, created_at, updated_at
document_chunks: id, document_id, content, chunk_index, created_at, updated_at
tasks: id, task_type, status, result, created_at, updated_at
queries: id, user_id, query_text, response, created_at, updated_at
```

**Milvus Vector Database**
```python
# Collection Schema
collection_name: "insightdocscollection"
fields:
  - id: VARCHAR (primary key)
  - document_id: VARCHAR
  - user_id: VARCHAR (Tenant Isolation)
  - text: VARCHAR  
  - dense_vector: FLOAT_VECTOR (768 dimensions)
  - sparse_vector: SPARSE_FLOAT_VECTOR (BM25)

# Index Configuration
index_type: IVF_FLAT
metric_type: COSINE
nlist: 128
```

**Redis**
- Celery message broker
- Task result backend
- Rate Limiting storage (sliding window)

**S3/MinIO**
- Original document storage
- Scalable file management

### 5. LLM Integration Layer

**Gemini API Client**
```python
class LLMClient:
    def summarize(text) -> str
    def extract_entities(text) -> List[str]
    def generate_rag_response(query, context) -> str
    def generate_quiz(content) -> List[dict]
    def generate_mindmap(content) -> dict
    def generate_suggestions(content) -> List[str]
    def recommend_option(options, criteria) -> str
```

**SentenceTransformers Embeddings**
```python
# Model: BAAI/bge-base-en-v1.5 (768 dimensions)
class EmbeddingEngine:
    @staticmethod
    def get_embedding_engine() -> EmbeddingEngine  # Singleton
    def generate_embeddings(texts) -> List[List[float]]
    def generate_single_embedding(text) -> List[float]
```

## Data Flow

### Document Upload Pipeline

```
1. Upload Request
   │
   ├── FastAPI endpoint receives file (in-memory)
   │
2. Object Storage Upload (before queuing)
   │
   ├── API uploads the file bytes directly to S3/MinIO
   ├── API creates the Document record in PostgreSQL with the
   │   resulting S3 bucket/object key already set
   │
3. Celery Task: process_document
   │
   ├── API queues (document_id, s3_key, filename, user_id) —
   │   never a local filesystem path, since the worker may run
   │   in a separate process or container from the API
   │
4. Worker Downloads Its Own Local Copy
   │
   ├── Worker verifies task ownership (document belongs to user_id)
   ├── Worker downloads the S3 object to a private local temp file
   │
5. Orchestrator Coordinates Workflow
   │
   ├── DataAgent parses the local temp copy (it does not upload —
   │   the file is already in object storage)
   ├── DataAgent chunks text into segments
   │
6. AnalysisAgent Processing
   │
   ├── Generate dense + sparse embeddings
   ├── Store vectors in Milvus (tagged with user_id and document_id)
   ├── Persist chunks to PostgreSQL — this step is fatal to the
   │   workflow if it fails, since a vector with no matching
   │   DocumentChunk row can never be hydrated into a citation
   ├── Auto-generate document summary
   │
7. Cleanup
   │
   ├── Worker deletes its local temp file in a finally block,
   │   regardless of whether processing succeeded or failed
   │
8. Complete
   │
   └── Document ready for querying
```

### RAG Query Pipeline

```
1. Query Request
   │
   ├── User submits natural language query, optionally scoped to a
   │   single document_id (e.g. from the document workspace view)
   ├── API validates JWT & Rate Limit (User-scoped)
   │
2. Orchestrator Processing
   │
   ├── Fetch User's decrypted API Key (BYOK)
   ├── If document_id was supplied, verify the user owns that
   │   document; otherwise the scope is silently ignored and
   │   retrieval falls back to searching all of the user's documents
   ├── Generate Query Embedding (Dense + Sparse)
   │
3. Vector Search (Hybrid)
   │
   ├── Milvus Hybrid Search (Dense + Sparse)
   ├── Filter: `user_id == current_user.id` (Strict Isolation),
   │   AND `document_id == <scoped_document_id>` when a verified
   │   document scope is present
   ├── Retrieve top-k candidates
   │
4. Context Assembly
   │
   ├── Rerank results (Cross-Encoder)
   ├── Verify Document DB ownership
   │
5. LLM Generation
   │
   ├── Gemini generates grounded response
   ├── Cite sources and chunks
   │
6. Response
   │
   └── Return answer with source attribution
```

## Authentication & Security

**Authentication**
- **JWT Implementation**: Access/Refresh tokens with bcrypt hashing.
- **Enforcement**: All document/query endpoints require valid JWT.
- **BYOK (Bring Your Own Key)**: Users provide Gemini API keys, stored with AES-256 encryption.

**Tenant Isolation**
- **Database**: All records filtered by `user_id`.
- **Vector DB**: Milvus queries enforced with `user_id` scalar filter.
- **Workers**: Tasks require explicit ownership validation before execution.

## Performance Characteristics

**Vector Search**
- Milvus IVF_FLAT index for fast similarity search
- COSINE metric optimized for semantic similarity
- 768-dimensional vectors balance accuracy and retrieval quality

**Async Processing**
- Non-blocking document processing
- Celery workers handle compute-intensive tasks
- FastAPI async endpoints for high concurrency

**Scalability**
- Horizontal scaling via additional Celery workers
- Milvus supports distributed vector search
- S3/MinIO provides unlimited storage capacity
