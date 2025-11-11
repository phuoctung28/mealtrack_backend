#!/bin/bash

echo "🛑 Stopping MealTrack..."
docker stop mealtrack_mysql 2>/dev/null
pkill -f "uvicorn src.api.main:app" 2>/dev/null
echo "✅ Stopped"