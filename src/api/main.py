import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect

from src.api.routes.v1.activities import router as activities_router
from src.api.routes.v1.daily_meals import router as daily_meals_router
from src.api.routes.v1.meal_plans import router as meal_plans_router
from src.api.routes.v1.meals import router as meals_router
from src.api.routes.v1.user_profiles import router as user_profiles_router

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database tables if they don't exist."""
    from src.infra.database.config import engine, Base
    
    # Import all models to ensure they're registered

    # Check if we should recreate tables (development mode)
    RECREATE_TABLES = os.getenv("RECREATE_TABLES", "false").lower() == "true"
    
    try:
        # Check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Count non-system tables
        app_tables = [t for t in existing_tables if t != 'alembic_version']
        
        if RECREATE_TABLES and app_tables:
            logger.warning("RECREATE_TABLES=true. Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            logger.info("All tables dropped.")
            app_tables = []
        
        if len(app_tables) == 0:
            logger.info("Creating database schema...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database schema created successfully!")
        else:
            logger.info(f"✅ Database ready with {len(app_tables)} existing tables")
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        logger.error("If using MySQL, ensure it's running: ./local.sh")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting MealTrack API...")
    
    # Initialize database
    init_database()
    
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
app.include_router(daily_meals_router)
app.include_router(user_profiles_router)

# Serve static files from uploads directory (development)
if os.environ.get('ENVIRONMENT') == 'development':
    uploads_path = os.getenv("UPLOADS_DIR", "./uploads")  # Default to './uploads' if UPLOADS_DIR is not set
    if os.path.exists(uploads_path):
        app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True) 