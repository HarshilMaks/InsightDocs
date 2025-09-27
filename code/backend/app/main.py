"""
Main Application Entry Point
Minimal setup for core API + database lifecycle
"""

from contextlib import asynccontextmanager
from typing import Dict, Any
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.database import startup_database, shutdown_database
from api import router



settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events"""
    await startup_database()
    yield
    await shutdown_database()


# FastAPI app
app = FastAPI(
    title=settings.app.app_name,
    version=settings.app.version,
    description="InsightOps - Cloud-native RAG Platform",
    lifespan=lifespan,
)


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(router, prefix=settings.app.api_prefix, tags=["InsightOps API"])


# Root
@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    return {
        "message": "Welcome to InsightOps API",
        "version": settings.app.version,
        "status": "healthy",
        "timestamp": time.time(),
    }


# Health
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": settings.app.app_name,
        "version": settings.app.version,
        "timestamp": time.time(),
    }