#!/bin/bash

echo "🍎 Starting MealTrack locally..."

# Setup virtual environment if it doesn't exist
# Using 3.12 for stability reasons
if [ ! -d "venv" ]; then
    echo "🔨 Creating virtual environment with Python 3.12..."
    python3.12 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

if ! podman ps | grep -q mealtrack_mysql; then
    echo "🐳 Starting MySQL..."
    podman run -d --name mealtrack_mysql \
        -e MYSQL_ROOT_PASSWORD=rootpassword123 \
        -e MYSQL_DATABASE=mealtrack \
        -e MYSQL_USER=mealtrack_user \
        -e MYSQL_PASSWORD=mealtrack_pass123 \
        -p 3306:3306 \
        mysql:8.0 2>/dev/null || podman start mealtrack_mysql
    
    echo "⏳ Waiting for MySQL..."
    sleep 10
fi

# Setup development database if needed
echo "🔧 Setting up development database..."
python scripts/dev_setup.py

# Start app
echo "✅ Ready! Starting at http://localhost:8000"
echo "📚 Docs at http://localhost:8000/docs"
echo ""
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
