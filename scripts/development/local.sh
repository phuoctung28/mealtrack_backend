#!/bin/bash

echo "Starting MealTrack locally (local PostgreSQL + Redis via Docker)..."

# ── 1. Virtual environment ────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip3 install -r requirements.txt -q

# ── 2. PostgreSQL (local Docker) ──────────────────────────────────────────────
PG_CONTAINER="mealtrack_postgres"
PG_USER="nutree"
PG_PASSWORD="nutree"
PG_DB="nutree"
PG_PORT="5432"

if ! docker ps | grep -q "$PG_CONTAINER"; then
    echo "Starting PostgreSQL..."
    docker run -d --name "$PG_CONTAINER" \
        -e POSTGRES_USER="$PG_USER" \
        -e POSTGRES_PASSWORD="$PG_PASSWORD" \
        -e POSTGRES_DB="$PG_DB" \
        -p "$PG_PORT:5432" \
        pgvector/pgvector:pg16 2>/dev/null || docker start "$PG_CONTAINER"

    echo "Waiting for PostgreSQL to be ready..."
    sleep 4
fi

export DATABASE_URL="postgresql://$PG_USER:$PG_PASSWORD@localhost:$PG_PORT/$PG_DB"

# ── 3. Redis ──────────────────────────────────────────────────────────────────
if ! docker ps | grep -q mealtrack_redis; then
    echo "Starting Redis..."
    docker run -d --name mealtrack_redis \
        -p 6379:6379 \
        redis:7-alpine 2>/dev/null || docker start mealtrack_redis

    echo "Waiting for Redis..."
    sleep 2
fi

# ── 4. Database initialisation ────────────────────────────────────────────────
echo "Running database setup..."
python3 scripts/init_postgres_db.py

# ── 5. Start app ──────────────────────────────────────────────────────────────
echo ""
echo "Ready! Starting at http://localhost:8000"
echo "Docs at http://localhost:8000/docs"
echo ""
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
