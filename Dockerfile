# ---- Stage 1: Builder ----
# This stage installs dependencies, including build-time tools.
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Set environment variables to prevent Python from writing .pyc files and to buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required for building some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies into the virtual environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: Final Image ----
# This stage creates the final, lean image for production.
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create a non-root user for security
RUN groupadd --system appuser && useradd --system --group appuser appuser

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code
# Ensure the source path matches your project structure
COPY ./code/backend/app ./app

# Create and set permissions for the uploads directory
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app/uploads

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Set the path to include the virtual environment's binaries
ENV PATH="/opt/venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Health check to ensure the API is responsive
# Corrected path to include the API prefix from your config
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Command to run the application in production
# Note: --reload is removed for production stability
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]