"""
Production-optimized FastAPI application.
Minimal startup overhead for faster deployment on Railway.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers with minimal overhead
from src.api.routes.v1.activities import router as activities_router
from src.api.routes.v1.meal_plans import router as meal_plans_router
from src.api.routes.v1.meals import router as meals_router
from src.api.routes.v1.user_profiles import router as user_profiles_router
from src.api.routes.v1.users import router as users_router

# No dotenv loading in production - use Railway's environment variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Minimal lifespan for production - no database initialization."""
    # Startup
    logger.info("Starting MealTrack API (Production)...")
    
    # In production, database should already be set up via migrations
    # No automatic table creation to prevent accidental data loss
    
    yield
    
    # Shutdown
    logger.info("Shutting down MealTrack API...")


# Create app without heavy initialization
app = FastAPI(
    title="MealTrack API",
    description="Production API for meal tracking and nutritional analysis",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None if os.getenv("DISABLE_DOCS", "false").lower() == "true" else "/docs",
    redoc_url=None if os.getenv("DISABLE_DOCS", "false").lower() == "true" else "/redoc",
)

# CORS configuration from environment
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "environment": "production"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "MealTrack API is running", "version": "0.2.0"}

# Include routers
app.include_router(meals_router)
app.include_router(activities_router)
app.include_router(meal_plans_router)
app.include_router(user_profiles_router)
app.include_router(users_router)

# No static file serving in production - use CDN or cloud storage