# .env Configuration Audit

**Date:** 2026-03-22  
**Status:** Complete Analysis

## Summary

After comprehensive codebase analysis, here's what's actually needed vs what's extra in your `.env` file.

---

## ✅ ESSENTIAL - Keep These (Actually Used)

### Application Settings
```bash
APP_NAME=InsightDocs              # Used in settings.py ✅
APP_ENV=development                # Used in settings.py ✅
APP_PORT=8000                      # Used in settings.py ✅
API_PREFIX=/api/v1                 # Used in settings.py ✅
DEBUG=True                         # Used in settings.py ✅
LOG_LEVEL=INFO                     # Used in settings.py ✅
```

### Security & Authentication
```bash
SECRET_KEY=bbdf3cf7bb645c1f6e0cd957796b33de    # ⚠️ CRITICAL - JWT signing ✅
ACCESS_TOKEN_EXPIRE_MINUTES=30                  # Used in settings.py ✅
ALLOWED_ORIGINS=http://localhost:3000,...       # Used in main.py CORS ✅
```

### Database (Choose ONE)
```bash
# Option 1: Neon Cloud (Production)
DATABASE_URL=postgresql://...                   # Used in settings.py ✅

# Option 2: Docker Local (Development)
POSTGRES_USER=insightdocs                       # Used by docker-compose ✅
POSTGRES_PASSWORD=insightdocs                   # Used by docker-compose ✅
POSTGRES_DB=insightdocs                        # Used by docker-compose ✅
POSTGRES_PORT=5432                             # Used by docker-compose ✅
```

### Redis & Celery
```bash
REDIS_URL=redis://localhost:6379/0            # Used in settings.py ✅
CELERY_BROKER_URL=redis://localhost:6379/0    # Used in celery_app.py ✅
CELERY_RESULT_BACKEND=redis://localhost:6379/1 # Used in celery_app.py ✅
```

### AI - Gemini (Required)
```bash
GEMINI_API_KEY=AIzaSyCo2NM...                 # ⚠️ SECRET - Used by LLM client ✅
GEMINI_MODEL=gemini-2.5-flash                 # Used in settings.py ✅
GEMINI_TEMPERATURE=0.7                        # Used in settings.py ✅
```

### Vector Database - Milvus/Zilliz (Required)
```bash
MILVUS_URI=https://in03-d183bf...             # ⚠️ SECRET - Used in embeddings.py ✅
MILVUS_TOKEN=8b813dfcece9a955...              # ⚠️ SECRET - Used in embeddings.py ✅
MILVUS_COLLECTION=insightdocscollection       # Used in settings.py ✅
MILVUS_DIM=768                                # Used in settings.py ✅
```

### Embeddings
```bash
VECTOR_DIMENSION=384                          # Used in settings.py (legacy) ✅
```

### Storage - S3/MinIO (Required)
```bash
S3_ENDPOINT=http://localhost:9000             # Used in file_storage.py ✅
AWS_ACCESS_KEY_ID=AKIAYRU7CPO62N3QG6GT       # ⚠️ SECRET - Used in file_storage.py ✅
AWS_SECRET_ACCESS_KEY=xqYkrIo7ReBBIHTt...    # ⚠️ SECRET - Used in file_storage.py ✅
S3_BUCKET_NAME=s3insightops                   # Used in file_storage.py ✅
```

### Docker MinIO (Development Only)
```bash
MINIO_ROOT_USER=minioadmin                    # Used by docker-compose ✅
MINIO_ROOT_PASSWORD=minioadmin                # Used by docker-compose ✅
MINIO_PORT=9000                               # Used by docker-compose ✅
MINIO_CONSOLE_PORT=9001                       # Used by docker-compose ✅
```

---

## ❌ EXTRA - Not Used (Can Remove Safely)

### Unused Variables
```bash
# Not referenced anywhere in the codebase:
REQUIRE_HTTPS=False                           # ❌ Not used
REDIS_PORT=6379                               # ❌ Redundant (in REDIS_URL)
MILVUS_METRIC=COSINE                          # ❌ Not read by code (hardcoded)
S3_UPLOAD_PREFIX=uploads/                     # ❌ Not used
LAMBDA_FUNCTION_NAME=insightops-file-processor # ❌ Not used (no Lambda)
AWS_DEFAULT_REGION=ap-south-1                 # ❌ Not used
DATABASE_POOL_SIZE=10                         # ❌ Not read by code
MAX_FILE_SIZE=104857600                       # ❌ Hardcoded in document_processor.py
REQUEST_TIMEOUT=300                           # ❌ Not used
TOKEN_LOGGING=True                            # ❌ Not used
METRICS_ENABLED=True                          # ❌ Not used
REACT_APP_API_URL=http://localhost:8000/api/v1 # ❌ Frontend var (not backend)
```

---

## ⚠️ WARNINGS & RECOMMENDATIONS

### 1. Secrets Exposed (SECURITY RISK!)
Your `.env` file contains real secrets that should NOT be in version control:

- ✅ `.env` is in `.gitignore` - GOOD!
- ❌ BUT check if you ever committed it before adding to `.gitignore`

**Critical Secrets:**
- `SECRET_KEY` - JWT signing key
- `GEMINI_API_KEY` - Google AI key
- `MILVUS_TOKEN` - Zilliz Cloud token
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - S3 credentials
- `DATABASE_URL` - Contains database password

**Action:** If these were ever committed to Git, rotate all keys immediately!

### 2. Database Configuration Conflict
You have TWO database configs:

```bash
# Neon Cloud (Production)
DATABASE_URL=postgresql://neondb_owner:...@ep-autumn-feather...

# Docker Local (Development)
POSTGRES_USER=insightdocs
POSTGRES_PASSWORD=insightdocs
```

**Current behavior:** App uses `DATABASE_URL` (Neon), Docker vars are for docker-compose only.

**Recommendation:** For local development, use Docker PostgreSQL:
```bash
DATABASE_URL=postgresql://insightdocs:insightdocs@localhost:5432/insightdocs
```

### 3. S3 Configuration Conflict
You're using MinIO locally but have AWS production credentials:

```bash
S3_ENDPOINT=http://localhost:9000              # ← MinIO local
AWS_ACCESS_KEY_ID=AKIAYRU7CPO62N3QG6GT         # ← AWS production
AWS_SECRET_ACCESS_KEY=xqYkrIo7ReBBIHTt...      # ← AWS production
```

**Issue:** Mixing local and production storage.

**Recommendation:** For local development:
```bash
S3_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=insightdocs-local
```

For production deployment, use real AWS credentials in Railway/Render environment variables.

### 4. Embedding Model Dimension Mismatch
```bash
VECTOR_DIMENSION=384          # Old model (all-MiniLM-L6-v2)
MILVUS_DIM=768                # New model (bge-base-en-v1.5)
```

**Status:** Using `MILVUS_DIM=768` (correct for upgraded model).  
**Action:** `VECTOR_DIMENSION` is kept for backward compatibility - OK to keep.

---

## 📋 RECOMMENDED CLEAN .env

### For Local Development

```bash
# ---------------------------------
# Application
# ---------------------------------
APP_NAME=InsightDocs
APP_ENV=development
APP_PORT=8000
API_PREFIX=/api/v1
DEBUG=True
LOG_LEVEL=INFO

# ---------------------------------
# Security & Auth
# ---------------------------------
# Generate new: openssl rand -hex 32
SECRET_KEY=your-secret-key-here-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# ---------------------------------
# Database (Docker Local)
# ---------------------------------
DATABASE_URL=postgresql://insightdocs:insightdocs@localhost:5432/insightdocs
POSTGRES_USER=insightdocs
POSTGRES_PASSWORD=insightdocs
POSTGRES_DB=insightdocs
POSTGRES_PORT=5432

# ---------------------------------
# Redis & Celery (Docker Local)
# ---------------------------------
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# ---------------------------------
# AI - Google Gemini
# ---------------------------------
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.7

# ---------------------------------
# Vector Database - Zilliz Cloud
# ---------------------------------
MILVUS_URI=your-zilliz-uri-here
MILVUS_TOKEN=your-zilliz-token-here
MILVUS_COLLECTION=insightdocscollection
MILVUS_DIM=768

# ---------------------------------
# Embeddings
# ---------------------------------
VECTOR_DIMENSION=384

# ---------------------------------
# Storage - MinIO (Docker Local)
# ---------------------------------
S3_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=insightdocs-local
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
```

### For Production Deployment

```bash
# Use environment variables in Railway/Render:
# - No .env file
# - Set each variable in platform dashboard
# - Use production credentials (AWS S3, Neon DB, etc.)
```

---

## 🔒 SECURITY CHECKLIST

Before deployment:

- [ ] Rotate `SECRET_KEY` (generate new one)
- [ ] Use production Gemini API key (not personal one)
- [ ] Use production AWS credentials (not development)
- [ ] Use managed PostgreSQL (Neon/Railway)
- [ ] Use managed Redis (Upstash/Railway)
- [ ] Enable HTTPS (`REQUIRE_HTTPS=True`)
- [ ] Restrict `ALLOWED_ORIGINS` to your domain
- [ ] Never commit `.env` to Git
- [ ] Use platform environment variables for production

---

## 📝 ACTION ITEMS

### Immediate (Before Testing)
1. ✅ Keep current `.env` for now (testing purposes)
2. ✅ Verify it's in `.gitignore`
3. ⚠️ Check Git history for accidental commits

### Before Production Deployment
1. 🔄 Create `.env.example` without secrets
2. 🔄 Generate new `SECRET_KEY`
3. 🔄 Use production credentials in Railway
4. 🔄 Remove unused variables
5. 🔄 Document required variables

### Optional Cleanup (Low Priority)
1. Remove unused variables from `.env`
2. Update `settings.py` to remove unused fields
3. Add validation for required variables

---

## 🎯 VERDICT

**Current .env Status:** ✅ Works but has extras

**Action Required:** 
- ✅ Safe to use for testing NOW
- 🔄 Clean up before production deployment
- ⚠️ Verify secrets aren't in Git history

**Variables to Remove (Safe):**
- `REQUIRE_HTTPS`
- `REDIS_PORT`
- `MILVUS_METRIC`
- `S3_UPLOAD_PREFIX`
- `LAMBDA_FUNCTION_NAME`
- `AWS_DEFAULT_REGION`
- `DATABASE_POOL_SIZE`
- `MAX_FILE_SIZE`
- `REQUEST_TIMEOUT`
- `TOKEN_LOGGING`
- `METRICS_ENABLED`
- `REACT_APP_API_URL`

**Total Savings:** 12 unnecessary variables (out of 72)

---

**Recommendation:** Keep current `.env` for testing, clean up later before deployment! 🚀
