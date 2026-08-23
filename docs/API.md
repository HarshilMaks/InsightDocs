# API Reference

Base URL: `http://localhost:8000/api/v1`

The generated OpenAPI documentation at [`/api/v1/docs`](http://localhost:8000/api/v1/docs) is the canonical request and response schema reference. This page is a stable endpoint index for the current product surface.

The authentication endpoints and the System routes explicitly marked below are public. All remaining endpoints require a bearer access token. Owner-scoped resources return `404` rather than exposing another user's document, workspace, history, audit, or review record.

## System

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Process status response; no API prefix. |
| `GET` | `/api/v1/live` | Lightweight liveness probe. |
| `GET` | `/api/v1/health` | Health check for API, PostgreSQL, and Redis. |

## Authentication and user configuration

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Register a user. The first registered user becomes an administrator. |
| `POST` | `/auth/login` | OAuth2-form login with `username` set to the user's email. |
| `POST` | `/auth/google` | Sign in with a Google identity token when Google sign-in is configured. |
| `PUT` | `/users/me/api-key` | Store an encrypted BYOK Gemini key. |
| `DELETE` | `/users/me/api-key` | Remove the current user's stored BYOK key. |
| `PATCH` | `/users/me/byok-settings` | Enable or disable BYOK use. |
| `GET` | `/users/me/byok-status` | Read BYOK configuration status without returning the key. |

## Documents and processing

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/documents/upload` | Upload a supported PDF, DOCX, PPTX, or text file up to 50 MB and queue processing. |
| `GET` | `/documents/` | List the authenticated user's documents. |
| `GET` | `/documents/{document_id}` | Read one owned document's state and metadata. |
| `GET` | `/documents/{document_id}/file-url` | Get an owner-checked, short-lived URL for the original file. |
| `DELETE` | `/documents/{document_id}` | Delete one owned document and its indexed content. |
| `POST` | `/documents/{document_id}/summarize` | Generate a document summary for a processed document. |
| `POST` | `/documents/{document_id}/quiz` | Generate a document quiz for a processed document. |
| `POST` | `/documents/{document_id}/mindmap` | Generate a document mind map for a processed document. |
| `GET` | `/tasks/` | List processing tasks. |
| `GET` | `/tasks/{task_id}` | Read one processing task state. |

## Evidence queries and history

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/query/` | Ask against exactly one ready document or an explicit Evidence Workspace. `document_id` and `workspace_id` are mutually exclusive. |
| `GET` | `/query/history` | Read the authenticated user's persisted query history. |

Query responses include answer text, citations, and Evidence Gate summary data. Citations include document and page context; new PDF ingestions can provide multiple precise bounding regions.

## Evidence Workspaces

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/workspaces` | List the authenticated user's private workspaces. |
| `POST` | `/workspaces` | Create a workspace with owned documents. |
| `GET` | `/workspaces/{workspace_id}` | Read one owned workspace and its members. |
| `PATCH` | `/workspaces/{workspace_id}` | Update a workspace name or description. |
| `DELETE` | `/workspaces/{workspace_id}` | Delete a workspace. |
| `PUT` | `/workspaces/{workspace_id}/documents/{document_id}` | Add an owned document to a workspace. |
| `DELETE` | `/workspaces/{workspace_id}/documents/{document_id}` | Remove a document from a workspace. |

A workspace query only retrieves the ready documents currently in that workspace. It never falls back to the full library.

## Evidence Gate review

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/evidence-gate/reviews` | List the current user's review queue. |
| `GET` | `/evidence-gate/reviews/{run_id}` | Read one owner-scoped audit and review record. |
| `POST` | `/evidence-gate/reviews/{run_id}/decisions` | Append an accept or reject decision using the record's review version. |

Evidence Gate is a shadow-mode assessment. Its records support human review but do not represent an automated truth determination.

## Administration

These endpoints require the administrator role.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/admin/users` | List users. |
| `PATCH` | `/admin/users/{user_id}/role` | Update a user's role. |
| `PATCH` | `/admin/users/{user_id}/deactivate` | Change a user's active state. |

## Error behavior

The API uses standard HTTP status codes. Important behavior includes:

- `401`: missing or invalid authentication.
- `403`: authenticated user lacks an administrative permission.
- `404`: the resource is absent or not owned by the caller.
- `409`: a document is not yet available for the requested action, or a review decision used a stale version.
- `422`: request validation failed, including attempting to send both `document_id` and `workspace_id` in one query.
- `499`: the server observed that the client disconnected during a query and did not persist the cancelled result.
