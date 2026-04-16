"""
Meal suggestion API endpoints (Phase 06).
Simplified to only include generation endpoint.
"""

import logging

from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import Response

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.middleware.accept_language import get_request_language
from src.api.middleware.rate_limit import limiter
from src.api.mappers.meal_suggestion_mapper import (
    to_suggestions_list_response,
    to_discovery_batch_response,
)
from src.api.schemas.request.meal_suggestion_requests import (
    MealSuggestionRequest,
    SaveMealSuggestionRequest,
    DiscoverMealsRequest,
    GenerateRecipesRequest,
)
from src.api.schemas.response.meal_suggestion_responses import (
    SuggestionsListResponse,
    SaveMealSuggestionResponse,
    DiscoveryBatchResponse,
    RecipeBatchResponse,
    FoodImageResponse,
)

logger = logging.getLogger(__name__)
from src.app.commands.meal_suggestion import (
    GenerateMealSuggestionsCommand,
    SaveMealSuggestionCommand,
    IngredientItem,
)
from src.infra.event_bus import EventBus

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
):
    """
    Lightweight discovery: single AI call → 6 meals with names + macros.
    No recipes/ingredients generated here — use POST /recipes for selected meals.
    Supports pagination via session_id — previously shown meals are auto-excluded.
    """
    try:
        import asyncio
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

        # --- meal-image-cache integration ---
        from src.api.dependencies.food_image import get_food_image_service
        from src.api.dependencies.meal_image_cache import (
            get_meal_image_cache_service, get_pending_queue,
        )
        from src.domain.model.meal_image_cache import PendingItem
        from src.domain.services.meal_image_cache.name_canonicalizer import slug as _slug
        from src.infra.config.settings import get_settings as _get_settings

        image_service = get_food_image_service()
        cfg = _get_settings()

        if cfg.MEAL_IMAGE_CACHE_ENABLED:
            from src.api.base_dependencies import get_db as _get_db
            _db = next(_get_db())
            cache_svc = await get_meal_image_cache_service(session=_db)
            pending_repo = await get_pending_queue(session=_db)
            english_names = [m["english_name"] for m in meals]
            cache_hits = await cache_svc.lookup_batch(english_names)
        else:
            cache_hits = [None] * len(meals)
            pending_repo = None

        images_list: list = []
        misses: list[PendingItem] = []
        for i, m in enumerate(meals):
            hit = cache_hits[i]
            if hit is not None:
                logger.info(
                    "image cache hit: meal=%r source=%s cosine=%.3f url=%s",
                    m["english_name"], hit.source, hit.cosine, hit.image_url,
                )
                images_list.append(hit)
                continue
            img_result = await image_service.search_food_image(m["english_name"])
            images_list.append(img_result)
            misses.append(PendingItem(
                meal_name=m["english_name"],
                name_slug=_slug(m["english_name"]),
                candidate_image_url=(img_result.url if img_result else None),
                candidate_thumbnail_url=(img_result.thumbnail_url if img_result else None),
                candidate_source=(img_result.source if img_result else None),
            ))

        if cfg.MEAL_IMAGE_CACHE_ENABLED and pending_repo and misses:
            await pending_repo.enqueue_many(misses)

        images = images_list
        # --- end integration ---

        # Translate names if non-English
        translated_names = [m["name"] for m in meals]
        if language != "en":
            from src.api.base_dependencies import get_translation_service
            try:
                translation_svc = get_translation_service()
                translated = await translation_svc.translate_names(
                    [m["name"] for m in meals], language
                )
                if translated and len(translated) == len(meals):
                    translated_names = translated
            except Exception as e:
                logger.warning(f"Name translation failed, using English: {e}")

        def _as_image_fields(x):
            """Accepts CachedImage (image_url attr) or FoodImageResult (url attr)."""
            if x is None:
                return dict(image_url=None, thumbnail_url=None, image_source=None,
                            photographer=None, photographer_url=None,
                            unsplash_download_location=None, image_confidence=0.0)
            image_url = getattr(x, "image_url", None) or getattr(x, "url", None)
            thumbnail_url = getattr(x, "thumbnail_url", None) or image_url  # fallback to full URL
            raw_source = getattr(x, "source", None)
            # TODO: remove once mobile handles "ai_generated" source — app currently
            # only renders images for "pexels"/"unsplash", so normalise unknown sources.
            image_source = raw_source if raw_source in ("pexels", "unsplash") else "pexels"
            return dict(
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                image_source=image_source,
                photographer=getattr(x, "photographer", None),
                photographer_url=getattr(x, "photographer_url", None),
                unsplash_download_location=getattr(x, "download_location", None),
                image_confidence=float(getattr(x, "confidence", 0.0) or 0.0),
            )

        # Build response
        from src.api.schemas.response.meal_suggestion_responses import (
            DiscoveryMealResponse, MacroEstimateResponse,
        )
        response_meals = []
        for i, m in enumerate(meals):
            img = images[i] if i < len(images) and not isinstance(images[i], Exception) else None
            meal_id = f"disc_{uuid.uuid4().hex[:12]}"
            response_meals.append(DiscoveryMealResponse(
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
            ))

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
            session, body.meal_names, "English",
            suggestion_count=len(body.meal_names),
            min_acceptable_override=1,
        )

        # Translate if non-English
        if language != "en" and recipes:
            from src.domain.services.meal_suggestion.parallel_recipe_generator import get_language_name
            recipes, _ = await service._recipe_generator._phase3_translate(
                session, recipes, get_language_name(language),
            )

        # Map to response
        from src.api.mappers.meal_suggestion_mapper import to_meal_suggestion_response
        return RecipeBatchResponse(
            recipes=[to_meal_suggestion_response(r) for r in recipes],
        )

    except Exception as e:
        raise handle_exception(e) from e


@router.get("/image", response_model=FoodImageResponse)
@limiter.limit("30/minute")
async def get_food_image(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="English food search query"),
    _user_id: str = Depends(get_current_user_id),
):
    """Search for a food image by query. Returns 200 with image data or 204 if not found."""
    try:
        from src.api.dependencies.food_image import get_food_image_service
        image_service = get_food_image_service()
        result = await image_service.search_food_image(q)
        if result is None:
            return Response(status_code=204)
        return FoodImageResponse(
            url=result.url,
            thumbnail_url=result.thumbnail_url,
            source=result.source,
            photographer=result.photographer,
        )
    except Exception as e:
        logger.warning(f"Food image search failed for query '{q}': {e}")
        return Response(status_code=204)


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
            calories=request.calories or round(request.protein * 4 + request.carbs * 4 + request.fat * 9),
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
                i.model_dump() if hasattr(i, 'model_dump') else i
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
            asyncio.create_task(
                UnsplashImageAdapter.trigger_download(request.unsplash_download_location)
            )

        return SaveMealSuggestionResponse(
            meal_id=meal_id,
            message="Meal suggestion saved successfully",
            meal_date=request.meal_date,
        )

    except Exception as e:
        raise handle_exception(e) from e
