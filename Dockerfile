# Multi-stage build for faster deployments
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first (for better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Set working directory
WORKDIR /app

COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser alembic.ini /app/
COPY --chown=appuser:appuser migrations/ /app/migrations/
COPY --chown=appuser:appuser docker-entrypoint.sh /app/

# Fix CRLF line endings (Windows-edited scripts) so script runs on Linux
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh
# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Ensure venv is in PATH
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV PYTHONUNBUFFERED=1

# Set worker count and disable auto-migration (migrations run via entrypoint)
ENV UVICORN_WORKERS=2
ENV AUTO_MIGRATE=false

# Health check (uses PORT at runtime; default 8000 in build)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/health\")" || exit 1

# Expose port (Railway sets PORT at runtime)
EXPOSE 8000

# Start the application via entrypoint (runs migrations first, then starts workers)
CMD ["/app/docker-entrypoint.sh"]