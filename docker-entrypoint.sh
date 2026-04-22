#!/bin/bash
set -e

echo "🚀 MealTrack Backend - Starting application..."

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Run database migrations (skip on Render where pre-deploy handles this)
if [ "${RENDER:-}" != "true" ]; then
    log "📦 Running database migrations..."
    if python migrations/run.py; then
        log "✅ Migrations completed successfully"
    else
        log "❌ Migrations failed!"
        exit 1
    fi
fi

# Render defaults web services to port 10000 if a custom port is not configured.
# Railway injects PORT; local Docker defaults to 8000.
if [ -z "${PORT:-}" ]; then
    if [ "${RENDER:-}" = "true" ]; then
        PORT="10000"
    else
        PORT="8000"
    fi
fi

# Start the application
log "🚀 Starting FastAPI application on port ${PORT}..."
WORKERS="${UVICORN_WORKERS:-4}"
log "Uvicorn workers: ${WORKERS}"
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --loop uvloop
