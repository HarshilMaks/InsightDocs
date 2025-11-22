# Architecture Guide

## System Overview

InsightDocs is built on a microservices-inspired architecture with multiple specialized agents coordinated by a central orchestrator.

## Components

### 1. Agent Layer

#### Base Agent Framework
All agents inherit from `BaseAgent` class providing:
- Standard message processing interface
- Error handling
- Event logging
- Message serialization

#### Orchestrator Agent
- Central coordinator for all workflows
- Routes tasks to appropriate agents
- Manages multi-step workflows
- Handles workflow failures and retries

#### Data Agent
Responsibilities:
- Document ingestion from various sources
- File storage management
- Data transformation and chunking
- Metadata extraction

#### Analysis Agent
Responsibilities:
- Embedding generation
- Content summarization
- Entity extraction
- Semantic analysis

#### Planning Agent
Responsibilities:
- Workflow planning
- Progress tracking
- Decision support
- Next-step suggestions

### 2. API Layer

FastAPI-based REST API providing:
- Document management endpoints
- Query/RAG endpoints
- Task monitoring endpoints
- Health checks

### 3. Worker Layer

Celery-based async task processing:
- Document processing pipeline
- Embedding generation
- Background cleanup tasks
- Scheduled periodic tasks

### 4. Data Layer

**PostgreSQL Database:**
- Documents metadata
- Task tracking
- Query history
- User data

**FAISS Vector Store:**
- Document embeddings
- Similarity search
- Metadata indexing

**Redis:**
- Message queue
- Task broker
- Result backend
- Caching

### 5. Storage Layer

S3/MinIO for:
- Raw document files
- Processed outputs
- Model artifacts
- Logs and reports

## Data Flow

### Document Ingestion Flow

```
1. User uploads document via API
   ↓
2. API creates Document record in DB
   ↓
3. Celery task starts async processing
   ↓
4. Orchestrator Agent coordinates:
   a. Data Agent: Ingest & store file
   b. Data Agent: Parse & chunk document
   c. Analysis Agent: Generate embeddings
   d. Data Agent: Store in vector DB
   ↓
5. Task status updated to "completed"
   ↓
6. Document ready for querying
```

### Query Flow (RAG)

```
1. User submits query via API
   ↓
2. Analysis Agent generates query embedding
   ↓
3. Vector search retrieves top-k similar chunks
   ↓
4. LLM Client constructs context
   ↓
5. Gemini generates response with citations
   ↓
6. Response saved to query history
   ↓
7. Return to user
```

## Message Queue Architecture

Agents communicate via Redis-based message queues:

**Queue Types:**
- Task queues: For Celery worker distribution
- Event streams: For real-time updates
- Result channels: For synchronous responses

**Message Format:**
```json
{
  "message_type": "task_request",
  "payload": { "task_specific_data": "..." },
  "sender_id": "agent_id",
  "recipient_id": "target_agent_id",
  "correlation_id": "request_tracking_id",
  "timestamp": "2024-01-01T00:00:00"
}
```

## Scalability Considerations

### Horizontal Scaling
- API: Multiple FastAPI instances behind load balancer
- Workers: Scale Celery workers independently
- Database: PostgreSQL replication for read scaling
- Redis: Redis Cluster for high availability

### Vertical Scaling
- Increase embedding model capacity
- Larger vector index for more documents
- More worker processes per machine

### Performance Optimization
- Connection pooling for database
- Embedding caching
- Batch processing for large documents
- Async I/O throughout

## Security Architecture

### Network Security
- API behind reverse proxy (nginx)
- Internal services on private network
- TLS/SSL for external communications

### Data Security
- Encrypted storage for sensitive documents
- Secrets management via environment variables
- PostgreSQL connection encryption
- S3 bucket policies and IAM roles

### Application Security
- Input validation on all endpoints
- SQL injection prevention via ORM
- Rate limiting on API endpoints
- Authentication/authorization (to be implemented)

## Monitoring & Observability

### Logging
- Structured JSON logging
- Agent-level event tracking
- Centralized log aggregation (future)

### Metrics
- Task completion rates
- Processing times
- Error rates
- Resource utilization

### Tracing
- Correlation IDs for request tracing
- Workflow execution tracking
- Performance profiling

## Deployment

### Development
- Docker Compose for local development
- Hot-reload for code changes
- Debug logging enabled

### Production
- Kubernetes deployment (future)
- Managed services (RDS, ElastiCache, S3)
- Auto-scaling policies
- Health checks and liveness probes

## Future Enhancements

1. **Agent Enhancements:**
   - More specialized agents (Validation, Compliance, etc.)
   - Agent-to-agent direct communication
   - Autonomous agent decision-making

2. **Infrastructure:**
   - Kubernetes orchestration
   - Service mesh (Istio)
   - GraphQL API option

3. **Features:**
   - Multi-tenancy support
   - Real-time collaboration
   - Advanced workflow builder
   - Custom agent plugins
