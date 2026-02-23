# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for n8n-workflows FastAPI application

# Stage 1: Builder (Python dependency resolution)
FROM python:3.12-slim as builder
WORKDIR /app

# Install build essentials for wheel compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-warn-script-location -r requirements.txt

# Stage 2: Development (with hot-reload and debug tools)
FROM python:3.12-slim as development
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORKFLOW_DB_PATH=/app/database/workflows.db

# Copy application source
COPY . .

# Create non-root user
RUN useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8000", "--dev"]

# Stage 3: Production (optimized runtime)
FROM python:3.12-slim as production
WORKDIR /app

LABEL org.opencontainers.image.title="n8n-workflows" \
      org.opencontainers.image.description="N8N Workflows FastAPI search engine" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.vendor="Production"

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Set PATH and environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2 \
    WORKFLOW_DB_PATH=/app/database/workflows.db \
    CI=true

# Copy application source (minimal)
COPY run.py run.py
COPY api_server.py api_server.py
COPY workflow_db.py workflow_db.py
COPY requirements.txt requirements.txt
COPY static/ static/
COPY workflows/ workflows/

# Create database directory and non-root user
RUN mkdir -p database && \
    useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8000", "--skip-index"]
