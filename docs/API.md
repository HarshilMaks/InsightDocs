# API Reference

Base URL: http://localhost:8000/api/v1

No auth required currently (auth infrastructure exists but not enforced).

## System

### GET / (root, no prefix)
Returns status, version, components

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "connected",
    "redis": "connected",
    "storage": "connected"
  }
}
```

### GET /api/v1/health
Real health check, pings PostgreSQL and Redis, returns healthy/degraded

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Authentication

### POST /api/v1/auth/register
Register a new user

**Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "password123"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z",
  "is_active": true
}
```

### POST /api/v1/auth/login
OAuth2 form login (username=email, password)

**Response:**
```json
{
  "token": {
    "access_token": "jwt_token_here",
    "refresh_token": "refresh_token_here",
    "token_type": "bearer"
  },
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2024-01-15T10:30:00Z",
    "is_active": true
  }
}
```

## Documents

### POST /api/v1/documents/upload
Upload document (multipart form, field: file)
Validates type (.txt,.pdf,.docx,.pptx) and size (max 50MB)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "success": true,
  "document_id": "uuid",
  "task_id": "task_uuid",
  "message": "Document uploaded successfully"
}
```

### GET /api/v1/documents/
List documents with pagination

**Query params:** skip (default 0), limit (default 100)

**Response:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "filename": "document.pdf",
      "file_type": "pdf",
      "file_size": 1024000,
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "processed_at": "2024-01-15T10:35:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/v1/documents/{document_id}
Get full document details

**Response:**
```json
{
  "id": "uuid",
  "filename": "document.pdf",
  "file_type": "pdf",
  "file_size": 1024000,
  "status": "completed",
  "content_preview": "Document content preview...",
  "chunk_count": 25,
  "created_at": "2024-01-15T10:30:00Z",
  "processed_at": "2024-01-15T10:35:00Z"
}
```

### DELETE /api/v1/documents/{document_id}
Delete document

**Response:**
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

### POST /api/v1/documents/{document_id}/summarize
Generate document summary (requires document status=completed)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/uuid/summarize"
```

**Response:**
```json
{
  "document_id": "uuid",
  "summary": "This document discusses key findings about..."
}
```

### POST /api/v1/documents/{document_id}/quiz
Generate quiz from document (requires document status=completed)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/uuid/quiz"
```

**Response:**
```json
{
  "document_id": "uuid",
  "quiz": [
    {
      "question": "What is the main topic?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "The correct answer is A because..."
    }
  ]
}
```

### POST /api/v1/documents/{document_id}/mindmap
Generate mindmap from document (requires document status=completed)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/uuid/mindmap"
```

**Response:**
```json
{
  "document_id": "uuid",
  "mindmap": {
    "central_topic": "Main Topic",
    "nodes": [
      {
        "id": "1",
        "label": "Subtopic 1",
        "group": "category1"
      }
    ],
    "edges": [
      {
        "source": "1",
        "target": "2",
        "label": "relates to"
      }
    ]
  }
}
```

## Query (RAG)

### POST /api/v1/query/
Query documents using RAG

**Body:**
```json
{
  "query": "What are the key findings?",
  "top_k": 5
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key findings?", "top_k": 5}'
```

**Response:**
```json
{
  "answer": "Based on the documents, the key findings are...",
  "sources": [
    {
      "document_id": "uuid",
      "document_name": "document.pdf",
      "content_preview": "Relevant content snippet...",
      "similarity_score": 0.85
    }
  ],
  "query_id": "query_uuid",
  "query": "What are the key findings?",
  "response_time": 1.23,
  "confidence_score": 0.92
}
```

### GET /api/v1/query/history
Get query history with pagination

**Query params:** skip, limit

**Response:**
```json
{
  "queries": [
    {
      "id": "uuid",
      "query": "What are the key findings?",
      "response": "The key findings are...",
      "response_time": 1.23,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

## Tasks

### GET /api/v1/tasks/{task_id}
Get task status

**Response:**
```json
{
  "task_id": "uuid",
  "status": "completed",
  "progress": 100,
  "result": {
    "document_id": "uuid",
    "chunks_processed": 25
  },
  "error": null
}
```

### GET /api/v1/tasks/
List tasks with pagination

**Query params:** skip, limit

**Response:**
```json
{
  "tasks": [
    {
      "id": "uuid",
      "task_type": "document_processing",
      "status": "completed",
      "progress": 100,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

## Error Handling

All errors return JSON in this format:
```json
{
  "detail": "error message"
}
```

**HTTP Status Codes:**
- 400 Bad Request - Invalid input or request
- 404 Not Found - Resource not found
- 500 Internal Server Error - Server error

## File Upload Constraints

**Supported file types:** .txt, .pdf, .docx, .pptx
**Maximum file size:** 50MB