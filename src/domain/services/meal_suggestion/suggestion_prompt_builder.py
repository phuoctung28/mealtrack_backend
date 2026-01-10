"""Prompt building for meal suggestions using PromptTemplateManager."""
from typing import Dict, List, Optional, TYPE_CHECKING

from src.domain.model.meal_planning import MealType, SimpleMacroTargets
from src.domain.services.prompts import PromptTemplateManager
from src.domain.services.prompts.prompt_constants import LANGUAGE_NAMES

if TYPE_CHECKING:
    from src.domain.model.meal_suggestion import SuggestionSession
    from src.domain.services.meal_suggestion.recipe_search_service import RecipeSearchResult


class SuggestionPromptBuilder:
    """Builds prompts for meal suggestion generation."""

    @staticmethod
    def build_meal_suggestion_prompt(
        meal_type: MealType, calorie_target: float, user_preferences: Dict
    ) -> str:
        """Build prompt for single meal generation (uses PromptTemplateManager)."""
        goal = user_preferences.get('goal', 'maintain_weight')
        dietary_prefs = user_preferences.get('dietary_preferences', [])
        health_conditions = user_preferences.get('health_conditions', [])
        target_macros = user_preferences.get('target_macros', {})
        activity_level = user_preferences.get('activity_level', 'moderately_active')
        
        total_target_calories = user_preferences.get('target_calories')
        if not total_target_calories:
            raise ValueError("target_calories is required in user_preferences")
        
        meal_percentage = calorie_target / total_target_calories
        
        if isinstance(target_macros, SimpleMacroTargets):
            protein_target = target_macros.protein * meal_percentage
            carbs_target = target_macros.carbs * meal_percentage
            fat_target = target_macros.fat * meal_percentage
        else:
            protein_target = target_macros.get('protein_grams', 50) * meal_percentage
            carbs_target = target_macros.get('carbs_grams', 250) * meal_percentage
            fat_target = target_macros.get('fat_grams', 65) * meal_percentage

        dietary_str = ", ".join(dietary_prefs) if dietary_prefs else "none"
        health_str = ", ".join(health_conditions) if health_conditions else "none"
        goal_guidance = PromptTemplateManager.get_goal_guidance(goal)
        
        # Compressed prompt using template manager
        return f"""Generate {meal_type.value} meal:

Profile: {goal} ({goal_guidance}) | Activity: {activity_level}
Diet: {dietary_str} | Health: {health_str}

Targets: {int(calorie_target)}cal (±50), {int(protein_target)}g P, {int(carbs_target)}g C, {int(fat_target)}g F

Requirements: Practical ingredients, reasonable cook time, respect restrictions.

{PromptTemplateManager.get_json_schema("single_meal")}"""

    @staticmethod
    def build_unified_meal_prompt(
        meal_distribution: Dict[MealType, float], user_preferences: Dict
    ) -> str:
        """Build unified prompt for daily meals (compressed)."""
        goal = user_preferences.get('goal', 'maintain_weight')
        dietary_prefs = user_preferences.get('dietary_preferences', [])
        health_conditions = user_preferences.get('health_conditions', [])
        target_macros = user_preferences.get('target_macros', {})
        target_calories = user_preferences.get('target_calories', 2000)
        
        dietary_str = ", ".join(dietary_prefs) if dietary_prefs else "none"
        health_str = ", ".join(health_conditions) if health_conditions else "none"
        goal_guidance = PromptTemplateManager.get_goal_guidance(goal)
        
        # Build compact meal targets
        meal_targets = []
        for meal_type, calorie_target in meal_distribution.items():
            meal_pct = calorie_target / target_calories
            if isinstance(target_macros, SimpleMacroTargets):
                p, c, f = target_macros.protein * meal_pct, target_macros.carbs * meal_pct, target_macros.fat * meal_pct
            else:
                p = target_macros.get('protein_grams', 50) * meal_pct
                c = target_macros.get('carbs_grams', 250) * meal_pct
                f = target_macros.get('fat_grams', 65) * meal_pct
            
            meal_targets.append(
                PromptTemplateManager.build_meal_targets(
                    meal_type.value.title(), int(calorie_target), p, c, f
                )
            )
        
        return f"""Generate daily meal plan:

Profile: {goal} ({goal_guidance})
Diet: {dietary_str} | Health: {health_str}
Daily Total: {int(target_calories)} cal

Meal Targets:
{chr(10).join(meal_targets)}

Requirements: Practical, reasonable times, respect restrictions, complementary flavors.

{PromptTemplateManager.get_json_schema("daily_meal")}"""


def build_single_meal_prompt(
    session: "SuggestionSession",
    meal_index: int,
    inspiration_recipe: Optional["RecipeSearchResult"] = None,
) -> str:
    """
    Build compact prompt for single meal (uses PromptTemplateManager).
    Target: ~500 output tokens for fast generation.
    """
    ingredients_list = session.ingredients[:8] if session.ingredients else []
    
    # Protein rotation hint
    protein_keywords = ["chicken", "beef", "pork", "fish", "salmon", "tuna", "shrimp", "tofu", "egg", "lamb", "turkey"]
    proteins = [ing for ing in ingredients_list if any(p in ing.lower() for p in protein_keywords)]
    protein_hint = ""
    if len(proteins) > 1:
        protein_hint = f"Feature {proteins[meal_index % len(proteins)]} as main protein"
    
    return PromptTemplateManager.build_suggestion_prompt(
        meal_type=session.meal_type,
        target_calories=session.target_calories,
        cooking_time_minutes=session.cooking_time_minutes,
        ingredients=ingredients_list,
        allergies=getattr(session, "allergies", None),
        dietary_preferences=getattr(session, "dietary_preferences", None),
        protein_hint=protein_hint,
    )


def build_meal_names_prompt(
    session: "SuggestionSession", 
    exclude_meal_names: Optional[List[str]] = None
) -> str:
    """
    Phase 1: Generate 4 diverse meal names (uses PromptTemplateManager).
    Target: ~200 tokens.
    
    Args:
        session: The suggestion session with user preferences
        exclude_meal_names: List of meal names to avoid (for regeneration)
    """
    return PromptTemplateManager.build_meal_names_prompt(
        meal_type=session.meal_type,
        target_calories=session.target_calories,
        cooking_time_minutes=session.cooking_time_minutes,
        ingredients=session.ingredients[:4] if session.ingredients else [],
        language=session.language,
        allergies=getattr(session, "allergies", None),
        dietary_preferences=getattr(session, "dietary_preferences", None),
        exclude_meal_names=exclude_meal_names,
    )


def build_recipe_details_prompt(meal_name: str, session: "SuggestionSession") -> str:
    """
    Phase 2: Generate full recipe details (uses PromptTemplateManager).
    Target: ~400 tokens.
    """
    return PromptTemplateManager.build_recipe_details_prompt(
        meal_name=meal_name,
        meal_type=session.meal_type,
        target_calories=session.target_calories,
        cooking_time_minutes=session.cooking_time_minutes,
        language=session.language,
        ingredients=session.ingredients[:6] if session.ingredients else [],
        allergies=getattr(session, "allergies", None),
        dietary_preferences=getattr(session, "dietary_preferences", None),
    )


def get_language_name(code: str) -> str:
    """Get full language name from ISO 639-1 code."""
    return LANGUAGE_NAMES.get(code, "English")


def get_language_instruction(code: str) -> str:
    """Get language instruction for AI prompts."""
    return PromptTemplateManager.get_language_instruction(code)
