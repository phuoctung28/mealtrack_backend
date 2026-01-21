#!/bin/bash

echo "🚀 Starting MealTrack migration process..."

# Set error handling
set -e

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

log "📦 Running database migrations..."

# Use the unified migration runner
if [ -f "migrations/run.py" ]; then
    log "🐍 Running migrations with migration runner..."
    python migrations/run.py
    
    if [ $? -eq 0 ]; then
        log "✅ Migrations completed successfully"
    else
        log "❌ Migration failed"
        exit 1
    fi
else
    log "❌ migrations/run.py not found"
    log "💡 Falling back to direct alembic..."
    if command_exists alembic; then
        alembic upgrade head
        log "✅ Migrations completed successfully"
    else
        log "❌ Alembic not found, cannot run migrations"
        log "💡 Install with: pip install alembic"
        exit 1
    fi
fi

log "🚀 Migration process completed"