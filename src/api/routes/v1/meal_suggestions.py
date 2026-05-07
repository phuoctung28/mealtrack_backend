"""
Meal suggestion API endpoints (Phase 06).
Simplified to only include generation endpoint.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.api.base_dependencies import get_db
from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.mappers.meal_suggestion_mapper import (
    to_suggestions_list_response,
)
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.schemas.request.meal_suggestion_requests import (
    DiscoverMealsRequest,
    GenerateRecipesRequest,
    MealSuggestionRequest,
    SaveMealSuggestionRequest,
)
from src.api.schemas.response.meal_suggestion_responses import (
    DiscoveryBatchResponse,
    RecipeBatchResponse,
    SaveMealSuggestionResponse,
    SuggestionsListResponse,
)
from src.app.commands.meal_suggestion import (
    GenerateMealSuggestionsCommand,
    IngredientItem,
    SaveMealSuggestionCommand,
)
from src.infra.event_bus import EventBus

logger = logging.getLogger(__name__)


async def _fetch_images_parallel(
    names: list[str],
    search_fn: Callable[[str], Awaitable[Any]],
    timeout: float = 3.0,
) -> list[Any]:
    """Fetch images in parallel with per-item timeout and error isolation."""

    async def safe_fetch(name: str):
        try:
            return await asyncio.wait_for(search_fn(name), timeout=timeout)
        except Exception as e:
            logger.warning("Image fetch failed for %r: %s", name, e)
            return None

    return await asyncio.gather(*[safe_fetch(n) for n in names])


router = APIRouter(prefix="/v1/meal-suggestions", tags=["Meal Suggestions"])


@router.post("/generate", response_model=SuggestionsListResponse)
@limiter.limit("5/minute")
async def generate_suggestions(
    request: Request,
    body: MealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    [Phase 06] Generate 3 meal suggestions with session tracking.

    **Initial Generation (no session_id):**
    - Creates new session and generates 3 meal suggestions
    - Returns session_id for future regeneration

    **Regeneration (with session_id):**
    - Automatically excludes previously shown meals from the session
    - Generates 3 NEW different meal suggestions
    - No need for separate /regenerate endpoint!

    Uses meal_portion_type (snack/main/omad) to calculate target calories from user's TDEE.
    Session expires after 4 hours.

    Backward compatible: accepts deprecated meal_size (S/M/L/XL/OMAD) and maps to new types.

    Language preference is read from Accept-Language header.
    """
    try:
        # Get language from Accept-Language header via middleware
        language = get_request_language(request)

        portion_type = body.get_effective_portion_type()

        command = GenerateMealSuggestionsCommand(
            user_id=user_id,
            meal_type=body.meal_type,
            meal_portion_type=portion_type.value,
            ingredients=body.ingredients,
            time_available_minutes=(
                body.cooking_time_minutes.value if body.cooking_time_minutes else None
            ),
            session_id=body.session_id,
            language=language,
            # Strictly enforce 1 serving per suggestion regardless of client input.
            # Older clients may still send 2-4 but are coerced to 1 for consistency.
            servings=1,
            cooking_equipment=body.cooking_equipment,
            cuisine_region=body.cuisine_region,
            calorie_target=body.calorie_target,
            protein_target=body.protein_target,
            carbs_target=body.carbs_target,
            fat_target=body.fat_target,
        )

        session, suggestions = await event_bus.send(command)
        return to_suggestions_list_response(session, suggestions)

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/discover", response_model=DiscoveryBatchResponse)
@limiter.limit("5/minute")
async def discover_meals(
    request: Request,
    body: DiscoverMealsRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
    db: Session = Depends(get_db),
):
    """
    Lightweight discovery: single AI call → 6 meals with names + macros.
    No recipes/ingredients generated here — use POST /recipes for selected meals.
    Supports pagination via session_id — previously shown meals are auto-excluded.
    """
    try:
        import uuid

        language = get_request_language(request)
        portion_type = body.get_effective_portion_type()

        from src.api.base_dependencies import get_suggestion_orchestration_service

        service = get_suggestion_orchestration_service()

        session, meals = await service.generate_discovery(
            user_id=user_id,
            meal_type=body.meal_type,
            meal_portion_type=portion_type.value,
            ingredients=body.ingredients,
            cooking_time_minutes=(
                body.cooking_time_minutes.value if body.cooking_time_minutes else None
            ),
            session_id=body.session_id,
            language=language,
            cuisine_region=body.cuisine_region,
            calorie_target_override=body.calorie_target,
            protein_target=body.protein_target,
            carbs_target=body.carbs_target,
            fat_target=body.fat_target,
            count=body.batch_size,
        )

        # --- meal-image-cache integration (always enabled) ---
        from src.api.dependencies.food_image import get_food_image_service
        from src.api.dependencies.meal_image_cache import (
            get_meal_image_cache_service,
            get_pending_queue,
        )
        from src.domain.model.meal_image_cache import PendingItem
        from src.domain.services.meal_image_cache.name_canonicalizer import (
            slug as _slug,
        )

        image_service = get_food_image_service()
        cache_svc = await get_meal_image_cache_service(session=db)
        pending_repo = await get_pending_queue(session=db)
        english_names = [m["english_name"] for m in meals]
        cache_hits = await cache_svc.lookup_batch(english_names)

        # Separate cache hits from misses
        images_list: list = [None] * len(meals)
        miss_indices: list[int] = []
        miss_names: list[str] = []

        for i, m in enumerate(meals):
            hit = cache_hits[i]
            if hit is not None:
                logger.info(
                    "image cache hit: meal=%r source=%s cosine=%.3f url=%s",
                    m["english_name"],
                    hit.source,
                    hit.cosine,
                    hit.image_url,
                )
                images_list[i] = hit
            else:
                miss_indices.append(i)
                miss_names.append(m["english_name"])

        # Fetch cache misses in parallel
        if miss_names:
            miss_results = await _fetch_images_parallel(
                miss_names,
                image_service.search_food_image,
                timeout=3.0,
            )
            for idx, result in zip(miss_indices, miss_results):
                images_list[idx] = result

        # Build pending queue items for misses
        misses: list[PendingItem] = []
        for i in miss_indices:
            img_result = images_list[i]
            misses.append(
                PendingItem(
                    meal_name=meals[i]["english_name"],
                    name_slug=_slug(meals[i]["english_name"]),
                    candidate_image_url=(img_result.url if img_result else None),
                    candidate_thumbnail_url=(
                        img_result.thumbnail_url if img_result else None
                    ),
                    candidate_source=(img_result.source if img_result else None),
                )
            )

        if pending_repo and misses:
            await pending_repo.enqueue_many(misses)

        images = images_list
        # --- end integration ---

        # Translate meal names if non-English
        translated_names = [m["name"] for m in meals]
        if language and language != "en":
            from src.api.base_dependencies import get_deepl_suggestion_translation_service
            try:
                translation_svc = get_deepl_suggestion_translation_service()
                if translation_svc:
                    translated = await translation_svc.translate_names(
                        [m["name"] for m in meals], language
                    )
                    if translated and len(translated) == len(meals):
                        translated_names = translated
            except Exception as e:
                logger.warning("Name translation failed, using English: %s", e)

        def _as_image_fields(x):
            """Accepts CachedImage (image_url attr) or FoodImageResult (url attr)."""
            if x is None:
                return dict(
                    image_url=None,
                    thumbnail_url=None,
                    image_source=None,
                    photographer=None,
                    photographer_url=None,
                    unsplash_download_location=None,
                    image_confidence=0.0,
                )
            image_url = getattr(x, "image_url", None) or getattr(x, "url", None)
            thumbnail_url = (
                getattr(x, "thumbnail_url", None) or image_url
            )  # fallback to full URL
            return dict(
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                image_source=getattr(x, "source", None),
                photographer=getattr(x, "photographer", None),
                photographer_url=getattr(x, "photographer_url", None),
                unsplash_download_location=getattr(x, "download_location", None),
                image_confidence=float(getattr(x, "confidence", 0.0) or 0.0),
            )

        # Build response
        from src.api.schemas.response.meal_suggestion_responses import (
            DiscoveryMealResponse,
            MacroEstimateResponse,
        )

        response_meals = []
        for i, m in enumerate(meals):
            img = images[i] if i < len(images) else None
            meal_id = f"disc_{uuid.uuid4().hex[:12]}"
            response_meals.append(
                DiscoveryMealResponse(
                    id=meal_id,
                    meal_name=translated_names[i],
                    english_name=m["english_name"],
                    macros=MacroEstimateResponse(
                        calories=m["calories"],
                        protein=m["protein"],
                        carbs=m["carbs"],
                        fat=m["fat"],
                    ),
                    **_as_image_fields(img),
                )
            )

        shown_count = len(session.shown_meal_names)
        return DiscoveryBatchResponse(
            session_id=session.id,
            meals=response_meals,
            has_more=len(meals) >= 4 and shown_count < 30,
            meal_count=len(response_meals),
        )

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/recipes", response_model=RecipeBatchResponse)
@limiter.limit("5/minute")
async def generate_recipes(
    request: Request,
    body: GenerateRecipesRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate full recipes for 1-3 selected discovery meals.
    Called after user picks meals from the discovery grid.
    """
    try:
        import uuid

        language = get_request_language(request)

        from src.api.base_dependencies import get_suggestion_orchestration_service

        service = get_suggestion_orchestration_service()

        # Build a minimal session for recipe generation
        from src.domain.model.meal_suggestion import SuggestionSession

        session = SuggestionSession(
            id=f"recipe_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            meal_type=body.meal_type,
            meal_portion_type="main",
            target_calories=body.calorie_target or 500,
            ingredients=body.ingredients,
            cooking_time_minutes=body.cooking_time_minutes,
            language=language,
            cuisine_region=body.cuisine_region,
            protein_target=body.protein_target,
            carbs_target=body.carbs_target,
            fat_target=body.fat_target,
        )

        # Reuse existing Phase 2 recipe generation for selected names
        recipes = await service._recipe_generator._phase2_generate_recipes(
            session,
            body.meal_names,
            "English",
            suggestion_count=len(body.meal_names),
            min_acceptable_override=1,
        )

        # Translate if non-English (pass ISO code like "vi", not full name)
        if language != "en" and recipes:
            if service._recipe_generator._translation_service:
                recipes = await service._recipe_generator._translation_service.translate_meal_suggestions_batch(
                    recipes, language
                )

        # Map to response
        from src.api.mappers.meal_suggestion_mapper import to_meal_suggestion_response

        return RecipeBatchResponse(
            recipes=[to_meal_suggestion_response(r) for r in recipes],
        )

    except Exception as e:
        raise handle_exception(e) from e


@router.post("/save", response_model=SaveMealSuggestionResponse)
async def save_meal_suggestion(
    request: SaveMealSuggestionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    """
    Save a meal suggestion as a regular meal in the meals table.

    This creates a Meal entity populated with the suggestion's nutrition data
    for the specified date so that it participates in daily macros and history.
    """
    try:
        command = SaveMealSuggestionCommand(
            user_id=user_id,
            suggestion_id=request.suggestion_id,
            name=request.name,
            meal_type=request.meal_type,
            calories=request.calories
            or round(request.protein * 4 + request.carbs * 4 + request.fat * 9),
            protein=request.protein,
            carbs=request.carbs,
            fat=request.fat,
            description=request.description,
            estimated_cook_time_minutes=request.estimated_cook_time_minutes,
            ingredients=[
                IngredientItem(
                    name=i.name,
                    amount=i.amount,
                    unit=i.unit,
                    calories=i.calories,
                    protein=i.protein,
                    carbs=i.carbs,
                    fat=i.fat,
                )
                for i in request.ingredients
            ],
            instructions=[
                i.model_dump() if hasattr(i, "model_dump") else i
                for i in request.instructions
            ],
            portion_multiplier=request.portion_multiplier,
            meal_date=request.meal_date,
            cuisine_type=request.cuisine_type,
            origin_country=request.origin_country,
            emoji=request.emoji,
            image_url=request.image_url,
        )

        meal_id = await event_bus.send(command)

        # Unsplash API compliance: trigger download event (fire-and-forget)
        if request.unsplash_download_location:
            import asyncio
            from src.infra.adapters.unsplash_image_adapter import UnsplashImageAdapter

            task = asyncio.create_task(
                UnsplashImageAdapter.trigger_download(
                    request.unsplash_download_location
                )
            )
            task.add_done_callback(
                lambda t: (
                    logger.warning(
                        "Unsplash download trigger failed: %s", t.exception()
                    )
                    if t.exception()
                    else None
                )
            )

        return SaveMealSuggestionResponse(
            meal_id=meal_id,
            message="Meal suggestion saved successfully",
            meal_date=request.meal_date,
        )

    except Exception as e:
        raise handle_exception(e) from e
