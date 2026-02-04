#!/bin/bash
set -e

echo "🚀 MealTrack Backend - Starting initialization..."

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Run database migrations
log "📦 Running database migrations..."
python migrations/run.py

if [ $? -eq 0 ]; then
    log "✅ Migrations completed successfully"
else
    log "❌ Migrations failed!"
    exit 1
fi

# Railway (and others) inject PORT; default 8000 for local/Docker
PORT="${PORT:-8000}"

# Start RQ worker in background (same container)
if [ -n "${REDIS_URL}" ]; then
    log "🔧 Starting RQ worker in background..."
    rq worker default --url "${REDIS_URL}" &
    WORKER_PID=$!
    log "✅ RQ worker started with PID ${WORKER_PID}"

    # Forward termination signals to worker
    trap "log 'Stopping RQ worker...'; kill ${WORKER_PID}; wait ${WORKER_PID} || true" SIGINT SIGTERM
else
    log "⚠️  REDIS_URL not set; RQ worker will NOT start"
fi

# Uvicorn workers (keep low for 512MB instances)
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"
# Start the application
log "🚀 Starting FastAPI application on port ${PORT}..."
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "${UVICORN_WORKERS}" \
    --loop uvloop
