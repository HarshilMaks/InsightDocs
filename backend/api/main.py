"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# --- Updated Imports ---
from backend.api import documents, query, tasks, auth  # Import the new auth router
from backend.api.schemas import HealthResponse
from backend.models.schemas import Base  # Import Base from your merged models file
from backend.models.database import engine, get_db
from backend.config import settings  # Import your new settings

# --- Use settings for logging ---
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create database tables (this will now include your User table)
# Commented out temporarily - uncomment when database is running
# Base.metadata.create_all(bind=engine)

# --- Use settings for FastAPI app initialization ---
app = FastAPI(
    title=settings.app_name,
    description="AI-Driven Agent Architecture System for Document Intelligence",
    version="1.0.0",
    # Add API prefix to docs URLs
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc" # Also add redoc
)

# --- Use settings for CORS ---
if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- Include all routers with the API prefix ---
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(query.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)


@app.get("/", response_model=HealthResponse, tags=["System"])
async def root():
    """Root endpoint."""
    return {
        "status": "operational",
        "version": "1.0.0",
        "components": {
            "api": "operational",
            "database": "operational",
            "workers": "operational"
        }
    }


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint — pings actual services."""
    components = {"api": "healthy"}

    # Check PostgreSQL
    try:
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        components["database"] = "healthy"
    except Exception:
        components["database"] = "unhealthy"

    # Check Redis
    try:
        import redis as _redis
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        components["redis"] = "healthy"
    except Exception:
        components["redis"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in components.values()) else "degraded"
    return {"status": overall, "version": "1.0.0", "components": components}