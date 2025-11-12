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

# Check if alembic is available
if command_exists alembic; then
    log "🐍 Running migrations with Alembic..."
    alembic upgrade head
    log "✅ Migrations completed successfully"
else
    log "❌ Alembic not found, cannot run migrations"
    log "💡 Install with: pip install alembic"
    exit 1
fi

log "🚀 Migration process completed"