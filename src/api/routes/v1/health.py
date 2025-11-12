"""
Health check endpoints for monitoring and status.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns basic status to indicate the API is running.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "message": "API is running"
        }
    )


@router.get("/")
async def root():
    """
    Root endpoint with API information.
    
    Returns basic API metadata and documentation links.
    """
    return {
        "name": "MealTrack API",
        "version": "1.0.0",
        "description": "Meal tracking and nutritional analysis API",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }