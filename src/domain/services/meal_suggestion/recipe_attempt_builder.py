"""
Single-recipe generation attempt with macro validation and MealSuggestion assembly.
Used by ParallelRecipeGenerator for each individual recipe AI call.
"""
import asyncio
import logging
import uuid
from typing import Dict, List, Optional

from src.domain.model.meal_suggestion import (
    Ingredient,
    MacroEstimate,
    MealSuggestion,
    MealType,
    RecipeStep,
    SuggestionSession,
)
from src.domain.services.emoji_validator import validate_emoji
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.meal_suggestion.macro_validation_service import MacroValidationService

logger = logging.getLogger(__name__)

PARALLEL_SINGLE_MEAL_TOKENS = 4000
PARALLEL_SINGLE_MEAL_TIMEOUT = 35


async def attempt_recipe_generation(
    generation_service: MealGenerationServicePort,
    macro_validator: MacroValidationService,
    prompt: str,
    meal_name: str,
    index: int,
    model_purpose: str,
    recipe_system: str,
    session: SuggestionSession,
    is_retry: bool = False,
) -> Optional[MealSuggestion]:
    """
    Single AI call to generate one recipe. Returns MealSuggestion on success, None on failure.

    Args:
        generation_service: Port for calling the AI generation API
        macro_validator: Validates and corrects raw macro values
        prompt: Recipe-specific prompt text
        meal_name: Name of the meal being generated
        index: Slot index (0-3) for logging
        model_purpose: Model pool key ("recipe_primary" / "recipe_secondary")
        recipe_system: System prompt with JSON schema instructions
        session: Current suggestion session (used for fallback values)
        is_retry: Whether this is a retry attempt on an alternate model
    """
    marker = "[RETRY]" if is_retry else ""
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(
                generation_service.generate_meal_plan,
                prompt,
                recipe_system,
                "json",
                PARALLEL_SINGLE_MEAL_TOKENS,
                None,
                model_purpose,
            ),
            timeout=PARALLEL_SINGLE_MEAL_TIMEOUT,
        )

        ingredients: List[Dict] = raw.get("ingredients", [])
        recipe_steps: List[Dict] = raw.get("recipe_steps", [])
        prep_time: int = raw.get("prep_time_minutes") or session.cooking_time_minutes or 30

        if not ingredients or not recipe_steps:
            logger.warning(
                f"[PHASE-2-UNEXPECTED-EMPTY]{marker} index={index} | "
                f"ingredients={len(ingredients)} | steps={len(recipe_steps)}"
            )
            return None

        raw_macros = {
            "calories": raw.get("calories", session.target_calories),
            "protein": raw.get("protein", 20.0),
            "carbs": raw.get("carbs", 30.0),
            "fat": raw.get("fat", 10.0),
        }
        validated = macro_validator.validate_and_correct(raw_macros)

        _log_ingredient_coverage(session, ingredients, meal_name, index, marker)

        logger.info(
            f"[PHASE-2-SUCCESS]{marker} index={index} | "
            f"model_purpose={model_purpose} | meal_name={meal_name}"
        )

        return MealSuggestion(
            id=f"sug_{uuid.uuid4().hex[:16]}",
            session_id=session.id,
            user_id=session.user_id,
            meal_name=meal_name,
            description="",
            meal_type=MealType(session.meal_type),
            macros=MacroEstimate(
                calories=validated["calories"],
                protein=validated["protein"],
                carbs=validated["carbs"],
                fat=validated["fat"],
            ),
            ingredients=[Ingredient(**ing) for ing in ingredients],
            recipe_steps=[RecipeStep(**step) for step in recipe_steps],
            prep_time_minutes=prep_time,
            confidence_score=0.85,
            origin_country=raw.get("origin_country"),
            cuisine_type=raw.get("cuisine_type", "International"),
            emoji=validate_emoji(raw.get("emoji")),
        )

    except asyncio.TimeoutError:
        logger.warning(
            f"[PHASE-2-TIMEOUT]{marker} index={index} | "
            f"model_purpose={model_purpose} | meal_name={meal_name}"
        )
        return None
    except Exception as e:
        logger.warning(
            f"[PHASE-2-FAIL]{marker} index={index} | "
            f"model_purpose={model_purpose} | error_type={type(e).__name__} | error={e}"
        )
        return None


def _log_ingredient_coverage(
    session: SuggestionSession,
    ingredients: List[Dict],
    meal_name: str,
    index: int,
    marker: str,
) -> None:
    """Log a warning if user-specified ingredients are absent from the recipe."""
    if not session.ingredients or session.language != "en":
        return

    recipe_ing_names = " ".join(ing.get("name", "").lower() for ing in ingredients)
    meal_name_lower = meal_name.lower()

    def _found(user_ing: str) -> bool:
        ui = user_ing.lower().strip()
        prefix = ui[:max(4, len(ui) - 2)]
        return (
            ui in recipe_ing_names
            or prefix in recipe_ing_names
            or ui in meal_name_lower
            or prefix in meal_name_lower
        )

    missing = [ui for ui in session.ingredients if not _found(ui)]
    if missing:
        logger.warning(
            f"[PHASE-2-INGREDIENT-MISMATCH]{marker} index={index} | "
            f"missing={missing} | meal_name={meal_name}"
        )
