"""
Ingredient recognition API endpoints.
"""
import logging

from fastapi import APIRouter, Depends, Request

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.middleware.accept_language import get_request_language
from src.api.schemas.request import IngredientRecognitionRequest
from src.api.schemas.response import IngredientRecognitionResponse
from src.app.commands.ingredient import RecognizeIngredientCommand
from src.infra.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ingredients", tags=["Ingredients"])


@router.post("/recognize", response_model=IngredientRecognitionResponse)
async def recognize_ingredient(
    request: IngredientRecognitionRequest,
    http_request: Request,
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Recognize a food ingredient from an image.

    Takes a base64 encoded image and uses Gemini Vision AI to identify
    the primary food ingredient visible in the image.
    Respects Accept-Language header for translating the ingredient name.

    Returns:
    - name: Identified ingredient name (translated to user's language)
    - confidence: Confidence score between 0 and 1
    - category: Category (vegetable, fruit, protein, grain, dairy, seasoning, other)
    - success: Whether recognition was successful
    - message: Additional message (e.g., error details)
    """
    try:
        language = get_request_language(http_request)
        command = RecognizeIngredientCommand(
            image_data=request.image_data,
            language=language,
        )
        result = await event_bus.send(command)
        return IngredientRecognitionResponse(**result)

    except Exception as e:
        logger.error(f"Ingredient recognition endpoint error: {e}")
        raise handle_exception(e)


@router.get("/health")
async def ingredients_health():
    """Check if ingredient recognition service is healthy."""
    return {
        "status": "healthy",
        "service": "ingredient_recognition",
        "features": [
            "photo_ingredient_identification",
            "gemini_vision_ai",
            "confidence_scoring"
        ]
    }
