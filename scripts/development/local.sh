#!/bin/bash

echo "🍎 Starting MealTrack locally..."

# Setup virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🔨 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Use local Redis by default for dev
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

if ! docker ps | grep -q mealtrack_mysql; then
    echo "🐳 Starting MySQL..."
    docker run -d --name mealtrack_mysql \
        -e MYSQL_ROOT_PASSWORD=rootpassword123 \
        -e MYSQL_DATABASE=mealtrack \
        -e MYSQL_USER=mealtrack_user \
        -e MYSQL_PASSWORD=mealtrack_pass123 \
        -p 3306:3306 \
        mysql:8.0 2>/dev/null || docker start mealtrack_mysql
    
    echo "⏳ Waiting for MySQL..."
    sleep 10
fi

if ! docker ps | grep -q mealtrack_redis; then
    echo "🐳 Starting Redis..."
    docker run -d --name mealtrack_redis \
        -p 6379:6379 \
        redis:7-alpine 2>/dev/null || docker start mealtrack_redis

    echo "⏳ Waiting for Redis..."
    sleep 5
fi

# Run database migrations
echo "🔧 Running database migrations..."
python migrations/run.py

# Start RQ worker (background) for async endpoints
echo "🔧 Starting RQ worker..."
rq worker default --url "${REDIS_URL}" &
WORKER_PID=$!
trap "echo '🛑 Stopping RQ worker...'; kill ${WORKER_PID}; wait ${WORKER_PID} || true" SIGINT SIGTERM

# Start app
echo "✅ Ready! Starting at http://localhost:8000"
echo "📚 Docs at http://localhost:8000/docs"
echo ""
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload