#!/bin/bash

# Startup script that selects the right app based on environment

if [ "$ENVIRONMENT" = "production" ] || [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "Starting in PRODUCTION mode..."
    exec uvicorn src.api.main_prod:app --host 0.0.0.0 --port ${PORT:-8000}
else
    echo "Starting in DEVELOPMENT mode..."
    exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi