# syntax=docker/dockerfile:1.4

# -------- Builder stage --------------------------------------------------
FROM python:3.11-slim AS builder

# Add metadata labels
LABEL org.opencontainers.image.source="https://github.com/demola07/ai-data-capture-portal-api"
LABEL org.opencontainers.image.description="AI Data Capture Portal API"
LABEL org.opencontainers.image.licenses="MIT"

# Install build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Install Python dependencies into a temp location (/install)
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# -------- Runtime stage --------------------------------------------------
FROM python:3.11-slim AS runtime

# Install runtime dependencies for psycopg2 and curl for health checks
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 appuser

# Copy python dependencies from builder layer
COPY --from=builder /install /usr/local

# Set workdir and copy source code
WORKDIR /app

# Copy only necessary files (respect .dockerignore)
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Create directory for logs if needed
RUN mkdir -p /app/logs

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port for Uvicorn
EXPOSE 8000

# Add health check for Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || curl -f http://localhost:8000/ || exit 1

# Start the FastAPI application with production settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
