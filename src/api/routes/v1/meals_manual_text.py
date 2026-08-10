"""Manual meal creation and text parsing routes (authenticated + guest trial)."""

import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from src.api.base_dependencies import get_ai_model_manager, get_cache_service
from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.dependencies.guest_quota import get_guest_quota_service
from src.api.dependencies.task_manager import get_optional_task_manager
from src.api.exceptions import ValidationException, handle_exception
from src.api.mappers.meal_mapper import MealMapper
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.routes.v1.meals_route_helpers import parsed_food_item_to_response
from src.api.schemas.request.meal_requests import (
    CreateManualMealFromFoodsRequest,
    ParseMealTextRequest,
)
from src.api.schemas.response import ManualMealCreationResponse
from src.api.schemas.response.meal_responses import ParseMealTextResponse
from src.api.services.guest_parse_quota import (
    GuestParseQuotaService,
    QuotaAlreadyUsedError,
    QuotaInFlightError,
    QuotaUnavailableError,
    validate_install_id,
)
from src.app.commands.meal.create_manual_meal_command import (
    CreateManualMealCommand,
    CustomNutrition,
    ManualMealItem,
)
from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.infra.services.durable_write_service import (
    MANUAL_MEAL_CREATE_ACTION,
    DurableWriteConflictError,
    normalize_idempotency_key,
    resolve_or_conflict,
    save_durable_write,
)
from src.app.services.meal_value_insight_scheduler import (
    schedule_value_insight_generation,
)
from src.api.routes.v1.manual_meal_durable import manual_meal_fingerprint
from src.domain.ports.cache_port import CachePort
from src.domain.ports.meal_insight_ai_port import MealInsightAIPort
from src.domain.services.prompts.input_sanitizer import sanitize_user_description
from src.infra.event_bus import BackgroundTaskManager, EventBus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/manual", response_model=ManualMealCreationResponse)
async def create_manual_meal(
    request: Request,
    payload: CreateManualMealFromFoodsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
    cache_service: CachePort | None = Depends(get_cache_service),
    task_manager: BackgroundTaskManager | None = Depends(get_optional_task_manager),
    ai_manager: MealInsightAIPort = Depends(get_ai_model_manager),
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
) -> ManualMealCreationResponse:
    """
    Create a manual meal from USDA FDC items.

    Optional Idempotency-Key enables exact response replay for the same logical
    write. Omitting the header preserves legacy single-shot behavior.
    """
    try:
        try:
            idempotency_key = normalize_idempotency_key(idempotency_key_header)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        fingerprint: str | None = None
        if idempotency_key is not None:
            fingerprint = manual_meal_fingerprint(payload)
            try:
                existing = await resolve_or_conflict(
                    user_id=user_id,
                    action=MANUAL_MEAL_CREATE_ACTION,
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                )
            except DurableWriteConflictError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error_code": "IDEMPOTENCY_KEY_CONFLICT",
                        "message": "Idempotency-Key reused with a different payload",
                    },
                ) from exc
            if existing is not None:
                return ManualMealCreationResponse.model_validate(existing.response_body)

        items = []
        for i in payload.items:
            custom_nutrition = None
            if i.custom_nutrition:
                custom_nutrition = CustomNutrition(
                    calories_per_100g=i.custom_nutrition.calories_per_100g,
                    protein_per_100g=i.custom_nutrition.protein_per_100g,
                    carbs_per_100g=i.custom_nutrition.carbs_per_100g,
                    fat_per_100g=i.custom_nutrition.fat_per_100g,
                    fiber_per_100g=i.custom_nutrition.fiber_per_100g,
                    sugar_per_100g=i.custom_nutrition.sugar_per_100g,
                )
            items.append(
                ManualMealItem(
                    fdc_id=i.fdc_id,
                    name=i.name,
                    quantity=i.quantity,
                    unit=i.unit,
                    custom_nutrition=custom_nutrition,
                    allowed_units=[unit.model_dump() for unit in i.allowed_units],
                )
            )

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
        _t0 = time.perf_counter()
        meal = await event_bus.send(cmd)
        _elapsed_ms = (time.perf_counter() - _t0) * 1000
        logger.info(
            "manual_save timing: user=%s total_handler_ms=%.1f",
            user_id,
            _elapsed_ms,
        )
        schedule_value_insight_generation(
            task_manager,
            meal,
            language=get_request_language(request),
            cache_service=cache_service,
            ai_manager=ai_manager,
            event_bus=event_bus,
            user_id=user_id,
        )

        response = ManualMealCreationResponse(
            meal_id=meal.meal_id,
            status="success",
            message=f"Meal '{payload.dish_name}' created successfully",
            created_at=meal.created_at,
            meal_detail=MealMapper.to_detailed_response(
                meal,
                target_language=get_request_language(request),
            ),
        )
        if idempotency_key is not None and fingerprint is not None:
            try:
                await save_durable_write(
                    user_id=user_id,
                    action=MANUAL_MEAL_CREATE_ACTION,
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    response_status_code=status.HTTP_200_OK,
                    response_body=response.model_dump(mode="json"),
                    resource_id=response.meal_id,
                )
            except DurableWriteConflictError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error_code": "IDEMPOTENCY_KEY_CONFLICT",
                        "message": "Idempotency-Key reused with a different payload",
                    },
                ) from exc
        return response
    except HTTPException:
        raise
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

    User types "2 eggs and toast" → AI parses → returns structured items with nutrition.
    """
    try:
        sanitized_text = sanitize_user_description(payload.text)
        if not sanitized_text:
            raise ValidationException(
                message="Invalid or empty meal description.",
                error_code="INVALID_MEAL_TEXT",
            )
        language = get_request_language(request)
        command = ParseMealTextCommand(
            text=sanitized_text,
            language=language,
            user_id=user_id,
            current_items=payload.current_items,
        )
        app_response = await event_bus.send(command)

        api_items = [parsed_food_item_to_response(item) for item in app_response.items]
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


@router.post("/parse-text/guest-trial", response_model=ParseMealTextResponse)
@limiter.limit("5/minute")
async def parse_meal_text_guest_trial(
    request: Request,
    payload: ParseMealTextRequest,
    x_guest_install_id: str = Header(..., alias="X-Guest-Install-Id"),
    quota: GuestParseQuotaService = Depends(get_guest_quota_service),
    event_bus: EventBus = Depends(get_configured_event_bus),
) -> ParseMealTextResponse:
    """
    One-shot guest parse_text trial for AI Handshake pre-login flow.
    No meal is saved. One successful parse per guest install id (Postgres quota).
    """
    if not validate_install_id(x_guest_install_id):
        raise ValidationException(
            message="Invalid guest install id.",
            error_code="INVALID_GUEST_INSTALL_ID",
        )

    sanitized_text = sanitize_user_description(payload.text)
    if not sanitized_text:
        raise ValidationException(
            message="Invalid or empty meal description.",
            error_code="INVALID_MEAL_TEXT",
        )

    try:
        id_hash = await quota.reserve(x_guest_install_id)
    except QuotaAlreadyUsedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "AI_HANDSHAKE_TRIAL_USED",
                "message": "Your guest trial has already been used.",
                "details": {},
            },
        ) from exc
    except (QuotaUnavailableError, QuotaInFlightError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "AI_HANDSHAKE_SERVICE_UNAVAILABLE",
                "message": "The guest trial is temporarily unavailable. Please try again later.",
                "details": {},
            },
        ) from exc

    language = get_request_language(request)
    command = ParseMealTextCommand(
        text=sanitized_text,
        language=language,
        user_id=None,
        current_items=payload.current_items,
    )

    try:
        app_response = await event_bus.send(command)
    except Exception as exc:
        await quota.release_reservation(id_hash)
        raise handle_exception(exc) from exc

    await quota.mark_completed(id_hash)

    api_items = [parsed_food_item_to_response(item) for item in app_response.items]
    total_calories = sum(i.calories for i in api_items)

    return ParseMealTextResponse(
        items=api_items,
        total_calories=total_calories,
        total_protein=app_response.total_protein,
        total_carbs=app_response.total_carbs,
        total_fat=app_response.total_fat,
        emoji=app_response.emoji,
    )
