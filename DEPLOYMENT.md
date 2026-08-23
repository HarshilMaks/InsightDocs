# InsightDocs Deployment Guide

## Prerequisites

You need accounts/instances for these services:

| Service | Purpose | Recommended Provider |
|---|---|---|
| **PostgreSQL** | Relational data (users, documents, chunks, queries) | Neon, Supabase, or Render Postgres |
| **Redis** | Celery broker + rate limiting | Upstash Redis or Render Redis |
| **Milvus/Zilliz** | Vector search | Zilliz Cloud (free tier available) |
| **Object Storage** | Document files | AWS S3, Cloudflare R2, or Backblaze B2 |
| **Python hosting** | API + Celery worker | Render (recommended) or Railway |
| **Frontend hosting** | React SPA | Vercel (recommended) |

---

## Step 1: Provision Infrastructure

### PostgreSQL
- Create a database named `insightdocs`
- Note the connection URL: `postgresql://user:pass@host:port/insightdocs`

### Redis
- Create a Redis instance
- Note the URL: `redis://default:password@host:port/0`

### Zilliz Cloud (Milvus)
- Create a free cluster at https://cloud.zilliz.com
- Note the endpoint URL and API token
- The collection will be auto-created on first connection

### Object Storage (S3-compatible)
- Create a bucket named `insightdocs`
- Create access credentials (access key + secret key)
- Note the endpoint URL (for AWS S3 use `https://s3.amazonaws.com`, for R2 use your R2 endpoint)

---

## Step 2: Deploy Backend (Render)

### API Service
1. Create a **Web Service** on Render and connect your GitHub repo.
2. Choose the **Docker** runtime.
3. Settings:
   - **Dockerfile Path:** `Dockerfile`
   - **Build Command:** leave empty. The Dockerfile installs `requirements-prod.txt` into `/opt/venv` during the image build.
   - **Start Command / Docker Command:** leave empty. The image `CMD` runs `bash scripts/start_api.sh`.
   - **Plan:** Starter or higher (512 MB deployments must use sparse retrieval).

### Worker Service
1. Create a **Background Worker** on Render and connect the same repo.
2. Choose the **Docker** runtime.
3. Settings:
   - **Dockerfile Path:** `Dockerfile.worker`
   - **Build Command:** leave empty. Its Dockerfile installs dependencies during the image build.
   - **Start Command / Docker Command:** leave empty. The image `CMD` runs `bash scripts/start_worker.sh`.

> Do not set `bash scripts/render_build.sh` as a Build, Start, Docker, or
> Pre-Deploy command for either Docker service. It is only for native Python
> deployments; the Docker runtime intentionally executes as an unprivileged
> user after `/opt/venv` has already been built.

### Environment Variables (set on BOTH services)
```
APP_ENV=production
DEBUG=false
# Required for a 512 MB Render API/worker. This disables local PyTorch models.
EMBEDDING_MODE=sparse
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(64))">
# One variable, with every permitted browser origin separated by commas.
ALLOWED_ORIGINS=https://insightdocs.vercel.app,http://localhost:3000,http://127.0.0.1:3000
DATABASE_URL=<your postgres URL>
REDIS_URL=<your redis URL>
CELERY_BROKER_URL=<same as REDIS_URL>
CELERY_RESULT_BACKEND=<redis URL with /1 suffix>
MILVUS_URI=<your Zilliz endpoint>
MILVUS_TOKEN=<your Zilliz token>
S3_ENDPOINT=<your S3/R2 endpoint>
AWS_ACCESS_KEY_ID=<your key>
AWS_SECRET_ACCESS_KEY=<your secret>
S3_BUCKET_NAME=insightdocs
GEMINI_MODEL=gemini-3.6-flash
GEMINI_MODEL_FALLBACKS=gemini-3-flash-preview
```

### GitHub Actions Worker (free hosted alternative)

If a paid Render Background Worker is not an option, the repository includes
`.github/workflows/process-celery-queue.yml`. It starts one Celery consumer for
up to twelve minutes every fifteen minutes, and can also be run manually from
**GitHub → Actions → Process InsightDocs queue → Run workflow**.

Add these **Repository secrets** in **GitHub → Settings → Secrets and variables
→ Actions**. Copy each production value exactly from the Render API service:

```
SECRET_KEY
DATABASE_URL
REDIS_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
MILVUS_URI
MILVUS_TOKEN
MILVUS_COLLECTION
MILVUS_DIM
S3_ENDPOINT
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
S3_BUCKET_NAME
AWS_DEFAULT_REGION
```

`GEMINI_API_KEY` is optional: add it only if you use a system-level Gemini
fallback in addition to user BYOK keys.

`SECRET_KEY` must match the API service so the worker can decrypt users' BYOK
keys. The workflow processes one task at a time and does not require a public
HTTP endpoint. A newly uploaded document can wait up to fifteen minutes before
a scheduled runner begins it; use **Run workflow** to start a run immediately.

---

## Step 3: Deploy Frontend (Vercel)

1. Import the repo on Vercel
2. Set **Root Directory** to `frontend`
3. Framework: Vite (auto-detected)
4. Environment Variables:
   ```
   VITE_API_BASE_URL=https://your-render-api-url.onrender.com/api/v1
   ```
5. Deploy

The `vercel.json` in `frontend/` handles SPA routing and security headers automatically.

---

## Step 4: Verify Deployment

1. **Health check:** `curl https://your-api.onrender.com/api/v1/health`
   - Should return `{"status": "healthy", ...}`
2. **Register a user:** POST to `/api/v1/auth/register`
3. **Upload a document:** POST to `/api/v1/documents/upload`
4. **Query:** POST to `/api/v1/query/`
5. **Frontend:** Visit your Vercel URL, log in, upload a PDF, ask a question

---

## Deployment Checklist

- [ ] PostgreSQL provisioned and URL noted
- [ ] Redis provisioned and URL noted
- [ ] Zilliz Cloud cluster created, endpoint + token noted
- [ ] S3-compatible bucket created with credentials
- [ ] Render API service deployed with env vars set
- [ ] Render Worker service deployed with same env vars
- [ ] `alembic upgrade head` completed successfully before the API starts (check logs)
- [ ] `alembic current` reports `d8e4f1a2b903` or a later revision
- [ ] Vercel frontend deployed with `VITE_API_BASE_URL` pointing to Render API
- [ ] `ALLOWED_ORIGINS` on Render includes the Vercel frontend URL
- [ ] Health endpoint returns healthy
- [ ] Registration + login works
- [ ] Document upload + processing completes
- [ ] Query returns answer with citations
- [ ] PDF viewer loads and highlights citations

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| CORS errors in browser | `ALLOWED_ORIGINS` doesn't include frontend URL | Add your Vercel URL to `ALLOWED_ORIGINS` env var on Render |
| 503 on query | Milvus not connected | Verify `MILVUS_URI` and `MILVUS_TOKEN` are correct |
| Upload succeeds but processing fails | Worker not running or can't reach Redis | Check worker logs on Render; verify `CELERY_BROKER_URL` |
| "No module named..." errors | Missing dependency | Check that `requirements.txt` includes all needed packages |
| PDF viewer shows nothing | Presigned URL expired or S3 endpoint wrong | Verify `S3_ENDPOINT` is accessible from the client browser (not internal-only) |
| Alembic migration fails | Wrong database URL, stale image, or deployed source missing the recorded revision | Confirm the deployed commit contains the migration file, run `alembic heads` and `alembic current`, then deploy the matching revision. Do not stamp or delete `alembic_version` as a workaround. |

---

## Architecture Notes for Production

- The API runs `alembic upgrade head` before Uvicorn starts. A migration failure stops the deployment rather than serving against a mismatched schema. For multi-instance deployments, run migrations as a separate one-off job before rolling application instances.
- The Celery worker uses `--concurrency=2` by default — increase for higher throughput if your plan allows more CPU/RAM.
- Object storage presigned URLs are served directly to the browser for PDF viewing — ensure your S3 endpoint is publicly reachable (not behind a VPN).
- Structured JSON logs are emitted in production (`APP_ENV=production`) for log ingestion services.


## Evidence Gate deployment note

Evidence Gate review state is stored in PostgreSQL. Before rolling out a release that
contains it, take the normal database backup/snapshot and run migrations once against
the target database:

```bash
alembic upgrade head
alembic current
```

Confirm that the current revision is `d8e4f1a2b903` or a later revision. Then verify a
query still succeeds and, for an owner with an audit run, confirm `/review` can load the
queue/detail and handle a stale review decision with a visible conflict rather than an
overwrite. Do not expose the review endpoints to unauthenticated callers.
