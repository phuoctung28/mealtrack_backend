"""Mappers for meal suggestion domain to API responses."""

from typing import List

from src.api.schemas.response.meal_suggestion_responses import (
    MealSuggestionResponse,
    MacroEstimateResponse,
    IngredientResponse,
    RecipeStepResponse,
    SuggestionsListResponse,
    DiscoveryMealResponse,
    DiscoveryBatchResponse,
)
from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession


def to_meal_suggestion_response(suggestion: MealSuggestion) -> MealSuggestionResponse:
    """Convert domain MealSuggestion to API response."""
    return MealSuggestionResponse(
        id=suggestion.id,
        meal_name=suggestion.meal_name,
        emoji=suggestion.emoji,
        description=suggestion.description,
        macros=MacroEstimateResponse(
            calories=suggestion.macros.calories,
            protein=suggestion.macros.protein,
            carbs=suggestion.macros.carbs,
            fat=suggestion.macros.fat,
        ),
        ingredients=[
            IngredientResponse(
                name=ing.name,
                amount=ing.amount,
                unit=ing.unit,
            )
            for ing in suggestion.ingredients
        ],
        recipe_steps=[
            RecipeStepResponse(
                step=step.step,
                instruction=step.instruction,
                duration_minutes=step.duration_minutes,
            )
            for step in suggestion.recipe_steps
        ],
        prep_time_minutes=suggestion.prep_time_minutes,
        confidence_score=suggestion.confidence_score,
        origin_country=suggestion.origin_country,
        cuisine_type=suggestion.cuisine_type,
    )


def to_discovery_meal_response(
    suggestion: MealSuggestion,
    image=None,
) -> DiscoveryMealResponse:
    """Convert domain MealSuggestion to lightweight discovery response (no recipe)."""
    return DiscoveryMealResponse(
        id=suggestion.id,
        meal_name=suggestion.meal_name,
        emoji=suggestion.emoji,
        description=suggestion.description,
        macros=MacroEstimateResponse(
            calories=suggestion.macros.calories,
            protein=suggestion.macros.protein,
            carbs=suggestion.macros.carbs,
            fat=suggestion.macros.fat,
        ),
        ingredient_names=[ing.name for ing in suggestion.ingredients],
        prep_time_minutes=suggestion.prep_time_minutes,
        cuisine_type=suggestion.cuisine_type,
        origin_country=suggestion.origin_country,
        image_url=image.url if image else None,
        thumbnail_url=image.thumbnail_url if image else None,
        image_source=image.source if image else None,
        photographer=image.photographer if image else None,
        photographer_url=image.photographer_url if image else None,
        unsplash_download_location=image.download_location if image else None,
    )


def to_discovery_batch_response(
    session: SuggestionSession,
    suggestions: List[MealSuggestion],
    meal_images: dict = None,
) -> DiscoveryBatchResponse:
    """Convert session + suggestions to discovery batch response."""
    shown_count = len(session.shown_suggestion_ids)
    has_more = len(suggestions) >= 4 and shown_count < 30
    images = meal_images or {}
    return DiscoveryBatchResponse(
        session_id=session.id,
        meals=[
            to_discovery_meal_response(s, images.get(s.id))
            for s in suggestions
        ],
        has_more=has_more,
        meal_count=len(suggestions),
    )


def to_suggestions_list_response(
    session: SuggestionSession,
    suggestions: List[MealSuggestion],
) -> SuggestionsListResponse:
    """Convert session + suggestions to API response."""
    return SuggestionsListResponse(
        session_id=session.id,
        meal_type=session.meal_type,
        meal_portion_type=session.meal_portion_type,
        target_calories=session.target_calories,
        suggestions=[to_meal_suggestion_response(s) for s in suggestions],
        suggestion_count=len(suggestions),
        expires_at=session.expires_at,
    )


