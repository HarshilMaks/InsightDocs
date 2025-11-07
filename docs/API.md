# API Reference

## Overview

InsightDocs provides a RESTful API for document management, querying, and task monitoring.

Base URL: `http://localhost:8000`

## Authentication

Currently, the API does not require authentication. In production, implement OAuth2/JWT authentication.

## Endpoints

### Health Check

#### GET /health

Check the health status of the system.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "workers": "healthy",
    "redis": "healthy"
  }
}
```

### Documents

#### POST /documents/upload

Upload a document for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (binary)

**Response:**
```json
{
  "success": true,
  "document_id": 1,
  "task_id": "abc-123",
  "message": "Document uploaded successfully. Processing started."
}
```

#### GET /documents/

List all documents.

**Query Parameters:**
- `skip` (int, default: 0): Number of records to skip
- `limit` (int, default: 100): Maximum records to return

**Response:**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "document.pdf",
      "status": "completed",
      "created_at": "2024-01-01T00:00:00",
      "file_size": 12345
    }
  ],
  "total": 1
}
```

#### GET /documents/{document_id}

Get document details.

**Response:**
```json
{
  "id": 1,
  "filename": "document.pdf",
  "status": "completed",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:05:00",
  "file_size": 12345,
  "file_type": ".pdf",
  "metadata": {}
}
```

#### DELETE /documents/{document_id}

Delete a document.

**Response:**
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

### Query

#### POST /query/

Query documents using RAG (Retrieval-Augmented Generation).

**Request:**
```json
{
  "query": "What is the main topic?",
  "top_k": 5
}
```

**Response:**
```json
{
  "success": true,
  "query": "What is the main topic?",
  "answer": "The main topic is...",
  "sources": [
    {
      "text": "Relevant text chunk...",
      "metadata": {},
      "distance": 0.5
    }
  ],
  "metadata": {
    "top_k": 5,
    "sources_count": 3
  }
}
```

#### GET /query/history

Get query history.

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)

**Response:**
```json
{
  "queries": [
    {
      "id": 1,
      "query": "What is the main topic?",
      "response": "The main topic is...",
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

### Tasks

#### GET /tasks/{task_id}

Get task status.

**Response:**
```json
{
  "task_id": "abc-123",
  "status": "completed",
  "progress": 100.0,
  "result": {},
  "error": null
}
```

#### GET /tasks/

List all tasks.

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)

**Response:**
```json
{
  "tasks": [
    {
      "id": "abc-123",
      "task_type": "document_processing",
      "status": "completed",
      "progress": 100.0,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message"
}
```

Common HTTP status codes:
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

Currently not implemented. Consider adding rate limiting in production.

## Webhooks

Webhook support is planned for future releases.
