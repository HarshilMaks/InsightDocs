# ============================================
# Stage 1: Builder (Install dependencies)
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy the lightweight web-service dependency set. Heavy parsing/ML packages
# belong in a separately deployed worker, not the 512MB Render API process.
COPY requirements-prod.txt .

# Install Python dependencies to /opt/venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache -r requirements-prod.txt

# ============================================
# Stage 2: Runtime (Minimal final image)
# ============================================
FROM python:3.11-slim

WORKDIR /app

# The web service only needs curl for its local health check. OCR, office
# conversion, ImageMagick, and ML runtimes run only in a separate worker.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy ONLY application code (tests/docs excluded via .dockerignore)
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts

# Set Python path and use venv
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"

# Make scripts executable
RUN chmod +x scripts/*.sh

# Run as non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the Render default web port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c 'curl -f http://localhost:${PORT:-10000}/api/v1/health || exit 1'

# Default: run migrations then start API (same behavior in Docker, Render, and local)
# For the worker service, override this with: bash scripts/start_worker.sh
CMD ["bash", "scripts/start_api.sh"]
