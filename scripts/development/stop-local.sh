#!/bin/bash

echo "Stopping MealTrack..."
docker stop mealtrack_postgres 2>/dev/null
docker stop mealtrack_redis 2>/dev/null
pkill -f "uvicorn src.api.main:app" 2>/dev/null
echo "Stopped"
