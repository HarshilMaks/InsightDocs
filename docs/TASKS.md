# InsightDocs — Implementation Task Plan

> Backend-first approach. Each task is independent and builds on the previous one.
> Frontend comes after all backend tasks are complete.

---

## Phase 1: Fix Critical Gaps (Backend Foundation)

### Task 1 — Real PDF Parsing ✅
- **What**: Replace placeholder with actual PDF text extraction using PyPDF2
- **Files**: `backend/utils/document_processor.py`, `requirements.txt`

### Task 2 — Real DOCX Parsing ✅
- **What**: Replace placeholder with actual Word extraction using python-docx
- **Files**: `backend/utils/document_processor.py`, `requirements.txt`

### Task 3 — PPT Parsing Support ✅
- **What**: Add PowerPoint file parsing using python-pptx
- **Files**: `backend/utils/document_processor.py`, `requirements.txt`

### Task 4 — File Size Validation ✅
- **What**: Enforce 50MB upload limit, validate file types
- **Files**: `backend/api/documents.py`

### Task 5 — Fix Celery Async/Sync Mismatch ✅
- **What**: Wrap async agent calls with `asyncio.run()` in Celery tasks
- **Files**: `backend/workers/tasks.py`

---

## Phase 2: New Feature Endpoints (Backend Features)

### Task 6 — Summarize Endpoint ✅
- **What**: `POST /api/v1/documents/{id}/summarize`
- **Files**: `backend/api/documents.py`

### Task 7 — Quiz Generation Endpoint ✅
- **What**: `POST /api/v1/documents/{id}/quiz`
- **Files**: `backend/utils/llm_client.py`, `backend/api/documents.py`

### Task 8 — Mind Map Endpoint ✅
- **What**: `POST /api/v1/documents/{id}/mindmap`
- **Files**: `backend/utils/llm_client.py`, `backend/api/documents.py`

### Task 9 — Wire Summarization + Chunk Storage into Pipeline ✅
- **What**: Auto-generate summary on upload, persist chunks to PostgreSQL
- **Files**: `backend/agents/orchestrator.py`

---

## Phase 3: Frontend (After Backend Complete)

### Task 10 — Frontend App
- **What**: Build React frontend with drag-and-drop upload, summary view, chat, quiz, mind map
- **Status**: 🔲 TODO

---

## Verified ✅

- All parsers tested (TXT, PDF, DOCX, PPTX)
- All imports resolve
- FastAPI app loads with all 19 routes
- New dependencies installed (PyPDF2, python-docx, python-pptx)
