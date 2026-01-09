"""
Chat API routes.
Organized by feature area for better maintainability.
"""
from fastapi import APIRouter

from .message_routes import router as message_router
from .thread_routes import router as thread_router

# Main chat router that combines all sub-routers
router = APIRouter(prefix="/v1/chat", tags=["Chat"])

# Include sub-routers
router.include_router(thread_router)
router.include_router(message_router)

__all__ = ["router"]
