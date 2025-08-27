import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect

from src.api.routes.v1.activities import router as activities_router
from src.api.routes.v1.meal_plans import router as meal_plans_router
from src.api.routes.v1.meals import router as meals_router
from src.api.routes.v1.user_profiles import router as user_profiles_router
from src.api.routes.v1.users import router as users_router

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_database():
    """Verify database connection and migration status."""
    from src.infra.database.config import engine
    import time
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Just verify we can connect to the database
            # Don't create or modify any tables - that's what migrations are for!
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            
            logger.info("✅ Database connection verified")
            
            # Check if alembic_version table exists (indicates migrations have run)
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if 'alembic_version' in existing_tables:
                logger.info("✅ Database migrations are in place")
            else:
                logger.warning("⚠️  No migrations detected. Ensure migrations run before app startup.")
                # In production, this should never happen if migrations are properly configured
            
            break
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                if "localhost" in str(e) or "127.0.0.1" in str(e):
                    logger.error("If using MySQL locally, ensure it's running: ./local.sh")
                else:
                    logger.error("Database connection failed. Check Railway deployment.")
                raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting MealTrack API...")
    
    # Verify database connection and migration status
    verify_database()
    
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
    return {"status": "healthy"}

@app.get("/")
async def root():
    return "MealTrack API is running! Visit /docs for API documentation."

app.include_router(meals_router)
app.include_router(activities_router)
app.include_router(meal_plans_router)
# app.include_router(daily_meals_router)
app.include_router(user_profiles_router)
app.include_router(users_router)

# Serve static files from uploads directory (development)
if os.environ.get('ENVIRONMENT') == 'development':
    uploads_path = os.getenv("UPLOADS_DIR", "./uploads")  # Default to './uploads' if UPLOADS_DIR is not set
    if os.path.exists(uploads_path):
        app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 