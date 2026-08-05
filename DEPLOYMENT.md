# InsightDocs — Deployment Guide

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
1. Create a **Web Service** on Render
2. Connect your GitHub repo
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `bash scripts/start_api.sh`
   - **Environment:** Python 3.11
   - **Plan:** Starter or higher (needs 512MB+ RAM for embeddings)

### Worker Service
1. Create a **Background Worker** on Render
2. Connect the same repo
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `bash scripts/start_worker.sh`
   - **Environment:** Python 3.11

### Environment Variables (set on BOTH services)
```
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(64))">
ALLOWED_ORIGINS=https://your-app.vercel.app
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
```

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
- [ ] `alembic upgrade head` ran successfully on first API start (check logs)
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
| Alembic migration fails | Wrong DATABASE_URL | Verify the URL is correct and the database exists |

---

## Architecture Notes for Production

- The API starts by running `alembic upgrade head` (in `start_api.sh`) — this is safe for single-instance deployments. For multi-instance, run migrations as a separate one-off job before deploying.
- The Celery worker uses `--concurrency=2` by default — increase for higher throughput if your plan allows more CPU/RAM.
- Object storage presigned URLs are served directly to the browser for PDF viewing — ensure your S3 endpoint is publicly reachable (not behind a VPN).
- Structured JSON logs are emitted in production (`APP_ENV=production`) for log ingestion services.
