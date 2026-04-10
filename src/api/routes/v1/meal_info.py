"""
Meal info generation endpoint.

POST /v1/meal-info/generate
Returns meal name, nutrition description, and a food image.
"""
from fastapi import APIRouter, Depends, Request

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.middleware.rate_limit import limiter
from src.api.schemas.request.meal_info_requests import MealInfoRequest
from src.api.schemas.response.meal_info_responses import MealInfoResponse
from src.app.commands.meal_info import GenerateMealInfoCommand
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/meal-info", tags=["Meal Info"])


@router.post("/generate", response_model=MealInfoResponse)
@limiter.limit("10/minute")
async def generate_meal_info(
    request: Request,
    body: MealInfoRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Generate lightweight meal display data: name, nutrition description, and image.

    - **meal_name** or **ingredients** must be provided (not both required).
    - When macros (calories, protein, carbs, fat) are all provided the nutrition
      description is rule-based and instant.
    - The image is fetched via a 3-source cascade: SerpAPI → Unsplash → Gemini.
      If all sources fail, `image_url` is null.
    """
    try:
        command = GenerateMealInfoCommand(
            user_id=user_id,
            meal_name=body.meal_name,
            ingredients=body.ingredients,
            meal_type=body.meal_type,
            language=body.language,
            calories=body.calories,
            protein=body.protein,
            carbs=body.carbs,
            fat=body.fat,
        )

        meal_info = await event_bus.send(command)

        return MealInfoResponse(
            meal_name=meal_info.meal_name,
            nutrition_description=meal_info.nutrition_description,
            image_url=meal_info.image_url,
            image_source=meal_info.image_source,
        )

    except Exception as e:
        raise handle_exception(e) from e
