"""Mappers for meal suggestion domain to API responses."""
from typing import List

from src.domain.model.meal_suggestion import MealSuggestion, SuggestionSession
from src.api.schemas.response.meal_suggestion_responses import (
    MealSuggestionResponse,
    MacroEstimateResponse,
    IngredientResponse,
    RecipeStepResponse,
    SuggestionsListResponse,
    AcceptedMealResponse,
)


def to_meal_suggestion_response(suggestion: MealSuggestion) -> MealSuggestionResponse:
    """Convert domain MealSuggestion to API response."""
    return MealSuggestionResponse(
        id=suggestion.id,
        meal_name=suggestion.meal_name,
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
    )


def to_suggestions_list_response(
    session: SuggestionSession,
    suggestions: List[MealSuggestion],
) -> SuggestionsListResponse:
    """Convert session + suggestions to API response."""
    return SuggestionsListResponse(
        session_id=session.id,
        suggestions=[to_meal_suggestion_response(s) for s in suggestions],
        expires_at=session.expires_at,
    )


def to_accepted_meal_response(result: dict) -> AcceptedMealResponse:
    """Convert acceptance result to API response."""
    return AcceptedMealResponse(
        meal_id=result["meal_id"],
        meal_name=result["meal_name"],
        macros=MacroEstimateResponse(
            calories=result["adjusted_macros"].calories,
            protein=result["adjusted_macros"].protein,
            carbs=result["adjusted_macros"].carbs,
            fat=result["adjusted_macros"].fat,
        ),
        saved_at=result["saved_at"],
    )
