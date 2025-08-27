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

# Check if we're in Railway environment
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    log "🌐 Railway environment detected: $RAILWAY_ENVIRONMENT"
    log "📦 Running migrations for production deployment..."
    
    # Run migrations using Python script
    if command_exists python; then
        log "🐍 Running migrations with Python..."
        python scripts/railway_migrate.py
    elif command_exists python3; then
        log "🐍 Running migrations with Python3..."
        python3 scripts/railway_migrate.py
    else
        log "❌ Python not found, cannot run migrations"
        exit 1
    fi
    
    log "✅ Migrations completed successfully"
else
    log "🏠 Local environment detected"
    log "💡 Skipping migrations (run manually if needed: alembic upgrade head)"
fi

log "🚀 Migration process completed, ready to start application"