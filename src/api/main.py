import logging
import os
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from src.api.routes.v1.activities import router as activities_router
from src.api.routes.v1.feature_flags import router as feature_flags_router
from src.api.routes.v1.meal_plans import router as meal_plans_router
from src.api.routes.v1.meals import router as meals_router
from src.api.routes.v1.user_profiles import router as user_profiles_router
from src.api.routes.v1.users import router as users_router
from src.api.routes.v1.foods import router as foods_router
from src.api.routes.v1.manual_meals import router as manual_meals_router

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting MealTrack API...")
    
    logger.info("MealTrack API started successfully!")
    yield
    
    # Shutdown
    logger.info("Shutting down MealTrack API...")


app = FastAPI(
    title="MealTrack API",
    description="API for meal tracking, nutritional analysis with AI vision capabilities, and smart meal planning",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    try:
        # Quick database connection check
        from src.infra.database.config import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/")
async def root():
    return "MealTrack API is running! Visit /docs for API documentation."

app.include_router(meals_router)
app.include_router(activities_router)
app.include_router(feature_flags_router)
app.include_router(meal_plans_router)
# app.include_router(daily_meals_router)
app.include_router(user_profiles_router)
app.include_router(users_router)
app.include_router(foods_router)
app.include_router(manual_meals_router)

# Serve static files from uploads directory (development)
if os.environ.get('ENVIRONMENT') == 'development':
    uploads_path = os.getenv("UPLOADS_DIR", "./uploads")  # Default to './uploads' if UPLOADS_DIR is not set
    if os.path.exists(uploads_path):
        app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 