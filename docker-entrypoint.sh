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
# Start the application
log "🚀 Starting FastAPI application on port ${PORT}..."
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 2 \
    --loop uvloop
