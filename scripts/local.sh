#!/bin/bash

echo "🍎 Starting MealTrack locally..."

echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

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

# Start app
echo "✅ Ready! Starting at http://localhost:8000"
echo "📚 Docs at http://localhost:8000/docs"
echo ""
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
