"""
Application factory for creating FastAPI instances based on environment.
"""
import os
from typing import Optional

def create_app(environment: Optional[str] = None) -> "FastAPI":
    """
    Create FastAPI application based on environment.
    
    Args:
        environment: 'production', 'development', or None (auto-detect)
    
    Returns:
        FastAPI application instance
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        from src.api.main_prod import app
    else:
        from src.api.main import app
    
    return app


# For Railway/production deployments
if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production":
    app = create_app("production")
else:
    app = create_app("development")