"""
Meals API endpoints using event-driven architecture.
Clean separation with event bus pattern.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query, Request, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.base_dependencies import get_image_store
from src.api.exceptions import handle_exception, ValidationException
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.mappers.meal_mapper import MealMapper
from src.api.schemas.request.meal_requests import (
    EditMealIngredientsRequest,
    CreateManualMealFromFoodsRequest,
    ParseMealTextRequest,
)
from src.api.schemas.response import DetailedMealResponse, ManualMealCreationResponse
from src.api.schemas.response.meal_responses import ParseMealTextResponse
from src.api.schemas.progress_schemas import DailyBreakdownResponse, StreakResponse
from src.api.schemas.response.daily_nutrition_response import DailyNutritionResponse
from src.api.schemas.response.weekly_budget_response import WeeklyBudgetResponse
from src.app.commands.meal import EditMealCommand, FoodItemChange, CustomNutritionData
from src.app.commands.meal.create_manual_meal_command import (
    CreateManualMealCommand,
    CustomNutrition,
    ManualMealItem,
)
from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.commands.meal.delete_meal_command import DeleteMealCommand
from src.app.commands.meal.upload_meal_image_immediately_command import (
    UploadMealImageImmediatelyCommand,
)
from src.app.queries.meal import GetMealByIdQuery, GetDailyMacrosQuery, GetStreakQuery, GetDailyBreakdownQuery
from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery
from src.domain.services.prompts.input_sanitizer import sanitize_user_description
from src.infra.event_bus import EventBus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/meals", tags=["Meals"])


# File upload constraints
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/jpg"]

# Status mapping from domain to API
STATUS_MAPPING = {
    "PROCESSING": "pending",
    "ANALYZING": "analyzing",
    "ENRICHING": "analyzing",  # API doesn't have enriching status
    "READY": "ready",
    "FAILED": "failed",
    "INACTIVE": "inactive",
}


@router.post(
    "/image/analyze",
    status_code=status.HTTP_200_OK,
    response_model=DetailedMealResponse,
)
@limiter.limit("10/minute")
async def analyze_meal_image_immediate(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    target_date: Optional[str] = Query(
        None, description="Target date in YYYY-MM-DD format for meal association"
    ),
    user_description: Optional[str] = Query(
        None,
        description="Optional user context (max 200 chars): 'no sugar', 'grilled', etc.",
    ),
    event_bus: EventBus = Depends(get_configured_event_bus),
    image_store=Depends(get_image_store),
):
    """
    Send meal photo and return immediate meal analysis with nutritional data.

    Authentication required: User ID is automatically extracted from the Firebase token.
    Language preference is read from Accept-Language header.
    """
    try:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationException(
                message=f"Invalid file type. Only {', '.join(ALLOWED_CONTENT_TYPES)} are allowed.",
                error_code="INVALID_FILE_TYPE",
                details={
                    "content_type": file.content_type,
                    "allowed": ALLOWED_CONTENT_TYPES,
                },
            )

        contents = await file.read()

        if len(contents) > MAX_FILE_SIZE:
            raise ValidationException(
                message=f"File size exceeds maximum allowed ({MAX_FILE_SIZE // (1024*1024)} MB)",
                error_code="FILE_SIZE_EXCEEDS_MAXIMUM",
                details={"size": len(contents), "max_size": MAX_FILE_SIZE},
            )

        parsed_target_date = None
        if target_date:
            try:
                parsed_target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD format.",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": target_date},
                ) from e

        sanitized_description = None
        if user_description:
            sanitized_description = sanitize_user_description(user_description)

        language = get_request_language(request)

        command = UploadMealImageImmediatelyCommand(
            user_id=user_id,
            file_contents=contents,
            content_type=file.content_type,
            target_date=parsed_target_date,
            user_description=sanitized_description,
            language=language,
        )

        try:
            meal = await event_bus.send(command)
        except (RuntimeError, ValueError) as e:
            error_msg = str(e)
            logger.warning("Meal image analysis failed: %s", error_msg)
            raise ValidationException(
                message="Could not identify food in the image. Please try again with a food photo.",
                error_code="NOT_FOOD_IMAGE",
                details={"error_message": error_msg},
            ) from e

        if meal.status.value == "FAILED":
            error_message = meal.error_message or "Analysis failed"
            raise ValidationException(
                message=f"Failed to analyze meal image: {error_message}",
                error_code="FAILED_TO_ANALYZE_MEAL_IMAGE",
                details={"error_message": error_message},
            )

        image_url = None
        if meal.image:
            image_url = meal.image.url or image_store.get_url(meal.image.image_id)

        return MealMapper.to_detailed_response(meal, image_url, target_language=language)

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/manual", response_model=ManualMealCreationResponse)
async def create_manual_meal(
    payload: CreateManualMealFromFoodsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
) -> ManualMealCreationResponse:
    """
    Create a manual meal from USDA FDC items.

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        items = []
        for i in payload.items:
            custom_nutrition = None
            if i.custom_nutrition:
                custom_nutrition = CustomNutrition(
                    calories_per_100g=i.custom_nutrition.calories_per_100g,
                    protein_per_100g=i.custom_nutrition.protein_per_100g,
                    carbs_per_100g=i.custom_nutrition.carbs_per_100g,
                    fat_per_100g=i.custom_nutrition.fat_per_100g,
                )
            items.append(
                ManualMealItem(
                    fdc_id=i.fdc_id,
                    name=i.name,
                    quantity=i.quantity,
                    unit=i.unit,
                    custom_nutrition=custom_nutrition,
                )
            )

        # Parse target_date if provided
        target_date = None
        if payload.target_date:
            try:
                target_date = datetime.strptime(payload.target_date, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationException(
                    message="Invalid date format. Use YYYY-MM-DD",
                    error_code="INVALID_DATE_FORMAT",
                    details={"date": payload.target_date},
                ) from e

        cmd = CreateManualMealCommand(
            user_id=user_id,
            items=items,
            dish_name=payload.dish_name,
            meal_type=payload.meal_type,
            target_date=target_date,
            source=payload.source,
            emoji=payload.emoji,
        )
        meal = await event_bus.send(cmd)

        return ManualMealCreationResponse(
            meal_id=meal.meal_id,
            status="success",
            message=f"Meal '{payload.dish_name}' created successfully",
            created_at=meal.created_at,
        )
    except Exception as e:
        raise handle_exception(e) from e


@router.post("/parse-text", response_model=ParseMealTextResponse)
@limiter.limit("20/minute")
async def parse_meal_text(
    request: Request,
    payload: ParseMealTextRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
) -> ParseMealTextResponse:
    """
    Parse natural language meal description into structured food items using AI.

    User types "2 eggs and toast" → Gemini parses → returns structured items with nutrition.
    """
    try:
        # Use Accept-Language header as single source of truth for locale
        language = get_request_language(request)
        command = ParseMealTextCommand(
            text=payload.text,
            language=language,
            user_id=user_id,
            current_items=payload.current_items,
        )
        app_response = await event_bus.send(command)

        # Map app DTO to API response DTO
        from src.api.schemas.response.meal_responses import ParsedFoodItem
        from src.domain.model.nutrition.macros import Macros as MacrosModel
        api_items = [
            ParsedFoodItem(
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                calories=MacrosModel(
                    protein=item.protein,
                    carbs=item.carbs,
                    fat=item.fat,
                    fiber=item.fiber if hasattr(item, "fiber") and item.fiber else 0.0,
                ).total_calories,
                protein=item.protein,
                carbs=item.carbs,
                fat=item.fat,
                data_source=item.data_source,
                fdc_id=item.fdc_id,
            )
            for item in app_response.items
        ]
        total_calories = sum(i.calories for i in api_items)

        return ParseMealTextResponse(
            items=api_items,
            total_calories=total_calories,
            total_protein=app_response.total_protein,
            total_carbs=app_response.total_carbs,
            total_fat=app_response.total_fat,
            emoji=app_response.emoji,
        )
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Get the user's current and best logging streak.

    - current_streak: consecutive days logged up to today (streak not broken until end of day)
    - best_streak: longest consecutive run ever
    - last_logged_date: most recent date with a meal (YYYY-MM-DD), null if never logged
    """
    try:
        header_tz = request.headers.get("X-Timezone")
        query = GetStreakQuery(user_id=user_id, header_timezone=header_tz)
        result = await event_bus.send(query)
        return result
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/weekly/daily-breakdown", response_model=DailyBreakdownResponse)
async def get_daily_breakdown(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    week_start: Optional[str] = Query(
        None,
        description="Week start date (Monday) in YYYY-MM-DD format. Defaults to current week.",
    ),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Get 7-day macro breakdown (Mon–Sun) with consumed vs target per day.

    Returns an array of 7 entries, one per day, with calories/protein/carbs/fat
    consumed and base daily targets from the user's TDEE.
    """
    try:
        parsed_week_start = None
        if week_start:
            parsed_week_start = datetime.strptime(week_start, "%Y-%m-%d").date()

        header_tz = request.headers.get("X-Timezone")
        query = GetDailyBreakdownQuery(
            user_id=user_id,
            week_start=parsed_week_start,
            header_timezone=header_tz,
        )
        result = await event_bus.send(query)
        return result
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/{meal_id}", response_model=DetailedMealResponse)
async def get_meal(
    request: Request,
    meal_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
    image_store = Depends(get_image_store),
):
    """Get detailed information about a specific meal.

    Language preference is read from Accept-Language header.
    Requires authentication - users can only access their own meals.
    """
    try:
        # Send query with user_id for ownership check
        query = GetMealByIdQuery(meal_id=meal_id, user_id=user_id)
        meal = await event_bus.send(query)

        # Get image URL if available (injected via DI)
        image_url = None
        if meal.image:
            # Prefer persisted Cloudinary URL from upload response.
            # Avoid extra Cloudinary API calls unless URL is missing.
            image_url = meal.image.url or image_store.get_url(meal.image.image_id)

        # Get language from Accept-Language header via middleware
        language = get_request_language(request)

        # Use mapper to convert to response with translation support
        return MealMapper.to_detailed_response(
            meal, image_url, target_language=language
        )

    except Exception as e:
        raise handle_exception(e) from e


@router.delete("/{meal_id}")
async def delete_meal(
    meal_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """Mark a meal as INACTIVE (soft delete)."""
    try:
        command = DeleteMealCommand(meal_id=meal_id, user_id=user_id)
        result = await event_bus.send(command)
        return result
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/daily/macros", response_model=DailyNutritionResponse)
async def get_daily_macros(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Get daily macronutrient summary for all meals with user targets from TDEE.

    Authentication required: User ID is automatically extracted from the Firebase token.
    """
    try:
        # Parse date
        target_date = None
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Send query with user_id for TDEE targets
        header_tz = request.headers.get("X-Timezone")
        query = GetDailyMacrosQuery(
            user_id=user_id, target_date=target_date, header_timezone=header_tz,
        )
        result = await event_bus.send(query)

        # Use mapper to convert to response
        return MealMapper.to_daily_nutrition_response(result)

    except Exception as e:
        raise handle_exception(e) from e


@router.put("/{meal_id}/ingredients", response_model=None)
async def update_meal_ingredients(
    meal_id: str,
    request: EditMealIngredientsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Update meal ingredients and portions.

    Supports adding, removing, and modifying ingredients with automatic nutrition recalculation.
    Requires authentication - users can only modify their own meals.
    """
    try:

        logger.info("Updating meal ingredients for meal %s", meal_id)
        # Convert request to command
        food_item_changes = []
        for change_request in request.food_item_changes:
            custom_nutrition = None
            if change_request.custom_nutrition:
                custom_nutrition = CustomNutritionData(
                    calories_per_100g=change_request.custom_nutrition.calories_per_100g,
                    protein_per_100g=change_request.custom_nutrition.protein_per_100g,
                    carbs_per_100g=change_request.custom_nutrition.carbs_per_100g,
                    fat_per_100g=change_request.custom_nutrition.fat_per_100g,
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
                )
            )

        logger.info("Food item changes: %s", food_item_changes)

        command = EditMealCommand(
            meal_id=meal_id,
            user_id=user_id,
            dish_name=request.dish_name,
            food_item_changes=food_item_changes,
        )

        logger.info("Sending command to event bus: %s", command)
        result = await event_bus.send(command)
        return result

    except Exception as e:
        raise handle_exception(e) from e


@router.get("/weekly/budget", response_model=WeeklyBudgetResponse)
async def get_weekly_budget(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    week_start: Optional[str] = Query(
        None,
        description="Week start date in YYYY-MM-DD format (Monday). Defaults to current week."
    ),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Get weekly macro budget status.

    Returns current week's budget with consumed totals and adjusted daily targets.
    """
    try:
        # Parse week_start date
        target_date = None
        if week_start:
            target_date = datetime.strptime(week_start, "%Y-%m-%d").date()

        header_tz = request.headers.get("X-Timezone")
        query = GetWeeklyBudgetQuery(
            user_id=user_id, target_date=target_date, header_timezone=header_tz,
        )
        result = await event_bus.send(query)
        return result
    except Exception as e:
        raise handle_exception(e) from e
