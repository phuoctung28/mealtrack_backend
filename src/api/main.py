"""
Main application file for the MealTrack API.

This file initializes the FastAPI application, sets up middleware,
includes routes, and handles application lifecycle events.
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager

import firebase_admin
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from firebase_admin import credentials
from sqlalchemy import text

from src.api.base_dependencies import initialize_scheduled_notification_service
from src.api.middleware.dev_auth_bypass import add_dev_auth_bypass
from src.api.routes.v1.activities import router as activities_router
from src.api.routes.v1.feature_flags import router as feature_flags_router
from src.api.routes.v1.foods import router as foods_router

from src.api.routes.v1.meal_plans import router as meal_plans_router
from src.api.routes.v1.meals import router as meals_router
from src.api.routes.v1.notifications import router as notifications_router
from src.api.routes.v1.user_profiles import router as user_profiles_router
from src.api.routes.v1.users import router as users_router
from src.api.routes.v1.webhooks import router as webhooks_router
from src.api.routes.v1.health import router as health_router
from src.infra.database.config import engine
from src.infra.database.migration_manager import MigrationManager

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.

    Supports three methods (in priority order):
    1. Service account JSON file path via FIREBASE_CREDENTIALS (recommended for local development)
    2. Service account JSON string via FIREBASE_SERVICE_ACCOUNT_JSON (recommended for production)
    3. Default credentials (fallback for cloud environments)

    Environment Variables:
    - FIREBASE_CREDENTIALS: Path to service account JSON file
    - FIREBASE_SERVICE_ACCOUNT_JSON: Service account JSON as string
    """
    try:
        # Check if already initialized
        firebase_admin.get_app()
        logger.info("Firebase already initialized")
        return
    except ValueError:
        # Not initialized yet, proceed with initialization
        pass

    try:
        environment = os.getenv("ENVIRONMENT", "development")
        
        # Option 1: Check for service account file path
        credentials_path = os.getenv("FIREBASE_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with service account file (environment: %s)", environment)
            return

        # Option 2: Check for service account JSON string
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            try:
                service_account_dict = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized with service account JSON string (environment: %s)", environment)
                return
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in FIREBASE_SERVICE_ACCOUNT_JSON: %s", e)
                raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON contains invalid JSON") from e

        # Option 3: Fall back to default credentials
        firebase_admin.initialize_app()
        logger.info("Firebase initialized with default credentials (environment: %s)", environment)

    except Exception as e:
        logger.error("Failed to initialize Firebase: %s", e)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting MealTrack API...")

    # Initialize Firebase Admin SDK
    try:
        initialize_firebase()
    except Exception as e:
        logger.error("Failed to initialize Firebase: %s", e)
        raise

    # Run database migrations
    try:
        migration_manager = MigrationManager.from_environment(engine)
        success = migration_manager.initialize_and_migrate()

        if not success:
            logger.error("Database migrations failed!")
            # Optionally, you can decide to exit here or continue in degraded mode
            # For now, we'll log the error and continue
            if os.getenv("FAIL_ON_MIGRATION_ERROR", "false").lower() == "true":
                logger.error(
                    "Exiting due to migration failure (FAIL_ON_MIGRATION_ERROR=true)"
                )
                raise RuntimeError("Database migration failed")
    except Exception as e:
        logger.error("Failed to run migrations: %s", e)
        if os.getenv("FAIL_ON_MIGRATION_ERROR", "false").lower() == "true":
            raise

    # Initialize and start scheduled notification service
    scheduled_service = None
    try:
        logger.info("Initializing scheduled notification service...")
        scheduled_service = initialize_scheduled_notification_service()
        await scheduled_service.start()
        logger.info("Scheduled notification service started successfully!")
    except Exception as e:
        logger.error(f"Failed to start scheduled notification service: {e}")
        # Continue running the API even if notification service fails
    
    logger.info("MealTrack API started successfully!")
    yield

    # Shutdown
    logger.info("Shutting down MealTrack API...")
    
    # Stop scheduled notification service
    if scheduled_service:
        try:
            logger.info("Stopping scheduled notification service...")
            await scheduled_service.stop()
            logger.info("Scheduled notification service stopped successfully!")
        except Exception as e:
            logger.error(f"Error stopping scheduled notification service: {e}")


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

# Dev auth bypass: inject a fixed user during development
add_dev_auth_bypass(app)

# Include all routers
app.include_router(health_router)
app.include_router(meals_router)
app.include_router(activities_router)
app.include_router(feature_flags_router)
app.include_router(meal_plans_router)
# app.include_router(daily_meals_router)
app.include_router(user_profiles_router)
app.include_router(users_router)
app.include_router(foods_router)
app.include_router(webhooks_router)
app.include_router(notifications_router)

# Serve static files from uploads directory (development)
if os.environ.get("ENVIRONMENT") == "development":
    uploads_path = os.getenv(
        "UPLOADS_DIR", "./uploads"
    )  # Default to './uploads' if UPLOADS_DIR is not set
    if os.path.exists(uploads_path):
        app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
