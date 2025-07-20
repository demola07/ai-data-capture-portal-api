# -------- Builder stage --------------------------------------------------
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Install Python dependencies into a temp location (/install)
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# -------- Runtime stage --------------------------------------------------
FROM python:3.11-slim AS runtime

# Install runtime dependencies for psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 appuser

# Copy python dependencies from builder layer
COPY --from=builder /install /usr/local

# Set workdir and copy source code
WORKDIR /app
COPY . .

# Ensure ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port for Uvicorn
EXPOSE 8000

# Start the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
