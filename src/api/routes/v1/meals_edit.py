"""Meal edit routes — ingredients, photos, delete."""

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request

from src.api.base_dependencies import get_ai_model_manager, get_cache_service
from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.dependencies.task_manager import get_optional_task_manager
from src.api.exceptions import ValidationException
from src.api.middleware.accept_language import get_request_language
from src.api.schemas.request.meal_requests import (
    AttachMealPhotoRequest,
    EditMealIngredientsRequest,
)
from src.app.commands.meal import (
    CustomNutritionData,
    EditMealCommand,
    FoodItemChange,
    NutritionOverride,
)
from src.app.commands.meal.attach_meal_photo_command import AttachMealPhotoCommand
from src.app.commands.meal.delete_meal_command import DeleteMealCommand
from src.app.commands.meal.delete_meal_photo_command import DeleteMealPhotoCommand
from src.app.queries.meal import GetMealByIdQuery
from src.app.services.meal_value_insight_scheduler import (
    schedule_value_insight_generation,
)
from src.domain.ports.cache_port import CachePort
from src.domain.ports.meal_insight_ai_port import MealInsightAIPort
from src.infra.event_bus import BackgroundTaskManager, EventBus

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_uploaded_meal_photo_url(image_url: str, image_id: str) -> None:
    parsed = urlparse(image_url)
    if parsed.scheme != "https" or parsed.netloc != "res.cloudinary.com":
        raise ValidationException("image_url must be a Cloudinary secure URL")
    if image_id not in parsed.path:
        raise ValidationException("image_id does not match image_url")


@router.delete("/{meal_id}")
async def delete_meal(
    meal_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Hard-delete a meal (idempotent — returns success if already deleted)."""
    command = DeleteMealCommand(meal_id=meal_id, user_id=user_id)
    result = await event_bus.send(command)
    return result


@router.put("/{meal_id}/ingredients", response_model=None)
async def update_meal_ingredients(
    meal_id: str,
    payload: EditMealIngredientsRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
    cache_service: CachePort | None = Depends(get_cache_service),
    task_manager: BackgroundTaskManager | None = Depends(get_optional_task_manager),
    ai_manager: MealInsightAIPort = Depends(get_ai_model_manager),
):
    """
    Update meal ingredients and portions.

    Supports adding, removing, and modifying ingredients with automatic nutrition recalculation.
    Requires authentication - users can only modify their own meals.
    """
    logger.info("Updating meal ingredients for meal %s", meal_id)
    food_item_changes = []
    for change_request in payload.food_item_changes:
        custom_nutrition = None
        if change_request.custom_nutrition:
            custom_nutrition = CustomNutritionData(
                calories_per_100g=change_request.custom_nutrition.calories_per_100g,
                protein_per_100g=change_request.custom_nutrition.protein_per_100g,
                carbs_per_100g=change_request.custom_nutrition.carbs_per_100g,
                fat_per_100g=change_request.custom_nutrition.fat_per_100g,
                fiber_per_100g=change_request.custom_nutrition.fiber_per_100g,
                sugar_per_100g=change_request.custom_nutrition.sugar_per_100g,
            )

        food_item_changes.append(
            FoodItemChange(
                action=change_request.action,
                id=change_request.id,
                fdc_id=change_request.fdc_id,
                name=change_request.name,
                quantity=change_request.quantity,
                unit=change_request.unit,
                custom_nutrition=custom_nutrition,
                nutrition_override=(
                    NutritionOverride(
                        calories=change_request.nutrition_override.calories,
                        protein=change_request.nutrition_override.protein,
                        carbs=change_request.nutrition_override.carbs,
                        fat=change_request.nutrition_override.fat,
                    )
                    if change_request.nutrition_override
                    else None
                ),
                clear_nutrition_override=change_request.clear_nutrition_override,
                allowed_units=[
                    unit.model_dump() for unit in change_request.allowed_units
                ],
            )
        )

    command = EditMealCommand(
        meal_id=meal_id,
        user_id=user_id,
        dish_name=payload.dish_name,
        created_at=payload.created_at,
        meal_type=payload.meal_type,
        food_item_changes=food_item_changes,
        nutrition_override=(
            NutritionOverride(
                calories=payload.nutrition_override.calories,
                protein=payload.nutrition_override.protein,
                carbs=payload.nutrition_override.carbs,
                fat=payload.nutrition_override.fat,
            )
            if payload.nutrition_override
            else None
        ),
    )

    logger.info("Sending command to event bus: %s", command)
    result = await event_bus.send(command)
    meal = await event_bus.send(GetMealByIdQuery(meal_id=meal_id, user_id=user_id))
    schedule_value_insight_generation(
        task_manager,
        meal,
        language=get_request_language(http_request),
        cache_service=cache_service,
        ai_manager=ai_manager,
        event_bus=event_bus,
        user_id=user_id,
    )
    return result


@router.put("/{meal_id}/photo", response_model=None)
async def attach_meal_photo(
    meal_id: str,
    payload: AttachMealPhotoRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Attach an already-uploaded meal photo to an existing meal.

    Requires authentication - users can only modify their own meals.
    """
    _validate_uploaded_meal_photo_url(payload.image_url, payload.image_id)
    command = AttachMealPhotoCommand(
        meal_id=meal_id,
        user_id=user_id,
        image_id=payload.image_id,
        image_url=payload.image_url,
        image_format=payload.image_format,
        size_bytes=payload.size_bytes,
    )
    return await event_bus.send(command)


@router.delete("/{meal_id}/photo", response_model=None)
async def delete_meal_photo(
    meal_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Detach the saved meal photo from an existing meal.

    Requires authentication - users can only modify their own meals.
    """
    command = DeleteMealPhotoCommand(meal_id=meal_id, user_id=user_id)
    return await event_bus.send(command)
