"""Prompt building for meal suggestions."""
from typing import Dict, Any, Optional, TYPE_CHECKING
from src.domain.model.meal_planning import MealType, SimpleMacroTargets

if TYPE_CHECKING:
    from src.domain.model.meal_suggestion import SuggestionSession
    from src.domain.services.meal_suggestion.recipe_search_service import RecipeSearchResult


class SuggestionPromptBuilder:
    """Builds prompts for meal suggestion generation."""

    @staticmethod
    def build_meal_suggestion_prompt(
        meal_type: MealType, calorie_target: float, user_preferences: Dict
    ) -> str:
        """Build prompt for single meal generation."""
        # Extract user data
        goal = user_preferences.get('goal', 'maintain_weight')
        dietary_prefs = user_preferences.get('dietary_preferences', [])
        health_conditions = user_preferences.get('health_conditions', [])
        target_macros = user_preferences.get('target_macros', {})
        activity_level = user_preferences.get('activity_level', 'moderately_active')

        # Calculate macro targets for this meal
        total_target_calories = user_preferences.get('target_calories')
        if not total_target_calories:
            raise ValueError("target_calories is required in user_preferences")
        meal_percentage = calorie_target / total_target_calories

        # Handle both MacroTargets object and dict format
        if isinstance(target_macros, SimpleMacroTargets):
            protein_target = target_macros.protein * meal_percentage
            carbs_target = target_macros.carbs * meal_percentage
            fat_target = target_macros.fat * meal_percentage
        else:
            # Legacy dict format
            protein_target = target_macros.get('protein_grams', 50) * meal_percentage
            carbs_target = target_macros.get('carbs_grams', 250) * meal_percentage
            fat_target = target_macros.get('fat_grams', 65) * meal_percentage

        # Build dietary restrictions string
        dietary_str = ", ".join(dietary_prefs) if dietary_prefs else "none"
        health_str = ", ".join(health_conditions) if health_conditions else "none"

        # Goal-specific guidance
        goal_guidance = {
            'lose_weight': "Focus on high-volume, low-calorie foods with plenty of fiber and protein for satiety",
            'gain_weight': "Include calorie-dense, nutritious foods with healthy fats and complex carbs",
            'build_muscle': "Emphasize high protein content with complete amino acids",
            'maintain_weight': "Create balanced meals with appropriate portions"
        }

        prompt = f"""Generate a {meal_type.value} meal suggestion with these requirements:

User Profile:
- Fitness Goal: {goal} - {goal_guidance.get(goal, 'balanced nutrition')}
- Activity Level: {activity_level}
- Dietary Restrictions: {dietary_str}
- Health Conditions: {health_str}

Nutritional Targets for this meal:
- Calories: {int(calorie_target)} (±50 calories)
- Protein: {int(protein_target)}g
- Carbs: {int(carbs_target)}g
- Fat: {int(fat_target)}g

Requirements:
1. The meal should be practical and use common ingredients
2. Cooking time should be reasonable for {meal_type.value}
3. Must respect all dietary restrictions
4. Should support the user's fitness goal
5. Include variety and flavor

Return ONLY a JSON object with this structure:
{{
    "name": "Meal name",
    "description": "Brief appealing description",
    "prep_time": 10,
    "cook_time": 20,
    "calories": {int(calorie_target)},
    "protein": {int(protein_target)},
    "carbs": {int(carbs_target)},
    "fat": {int(fat_target)},
    "ingredients": ["ingredient 1 with amount", "ingredient 2 with amount"],
    "instructions": ["Step 1", "Step 2"],
    "is_vegetarian": true/false,
    "is_vegan": true/false,
    "is_gluten_free": true/false,
    "cuisine_type": "cuisine type"
}}"""

        return prompt

    @staticmethod
    def build_unified_meal_prompt(meal_distribution: Dict[MealType, float], user_preferences: Dict) -> str:
        """Build a unified prompt for generating all daily meals at once."""
        # Extract user data
        goal = user_preferences.get('goal', 'maintain_weight')
        dietary_prefs = user_preferences.get('dietary_preferences', [])
        health_conditions = user_preferences.get('health_conditions', [])
        target_macros = user_preferences.get('target_macros', {})
        activity_level = user_preferences.get('activity_level', 'moderately_active')
        target_calories = user_preferences.get('target_calories', 2000)

        # Build dietary restrictions string
        dietary_str = ", ".join(dietary_prefs) if dietary_prefs else "none"
        health_str = ", ".join(health_conditions) if health_conditions else "none"

        # Goal-specific guidance
        goal_guidance = {
            'lose_weight': "Focus on high-volume, low-calorie foods with plenty of fiber and protein for satiety",
            'gain_weight': "Include calorie-dense, nutritious foods with healthy fats and complex carbs",
            'build_muscle': "Emphasize high protein content with complete amino acids",
            'maintain_weight': "Create balanced meals with appropriate portions"
        }

        # Build meal targets string
        meal_targets = []
        for meal_type, calorie_target in meal_distribution.items():
            meal_percentage = calorie_target / target_calories

            # Handle both MacroTargets object and dict format
            if isinstance(target_macros, SimpleMacroTargets):
                protein_target = target_macros.protein * meal_percentage
                carbs_target = target_macros.carbs * meal_percentage
                fat_target = target_macros.fat * meal_percentage
            else:
                # Legacy dict format
                protein_target = target_macros.get('protein_grams', 50) * meal_percentage
                carbs_target = target_macros.get('carbs_grams', 250) * meal_percentage
                fat_target = target_macros.get('fat_grams', 65) * meal_percentage

            meal_targets.append(f"""
{meal_type.value.title()}:
- Calories: {int(calorie_target)} (±50 calories)
- Protein: {int(protein_target)}g
- Carbs: {int(carbs_target)}g
- Fat: {int(fat_target)}g""")

        meal_targets_str = "\n".join(meal_targets)

        prompt = f"""Generate a complete daily meal plan with these requirements:

User Profile:
- Fitness Goal: {goal} - {goal_guidance.get(goal, 'balanced nutrition')}
- Activity Level: {activity_level}
- Dietary Restrictions: {dietary_str}
- Health Conditions: {health_str}
- Total Daily Calories: {int(target_calories)}

Nutritional Targets for each meal:
{meal_targets_str}

Requirements:
1. All meals should be practical and use common ingredients
2. Cooking times should be reasonable for each meal type
3. Must respect all dietary restrictions across all meals
4. Should support the user's fitness goal
5. Include variety and flavor across the day
6. Ensure meals complement each other for a balanced day

Return ONLY a JSON object with this structure:
{{
    "meals": [
        {{
            "meal_type": "breakfast",
            "name": "Meal name",
            "description": "Brief appealing description",
            "prep_time": 10,
            "cook_time": 20,
            "calories": 500,
            "protein": 25,
            "carbs": 60,
            "fat": 15,
            "ingredients": ["ingredient 1 with amount", "ingredient 2 with amount"],
            "instructions": ["Step 1", "Step 2"],
            "is_vegetarian": true/false,
            "is_vegan": true/false,
            "is_gluten_free": true/false,
            "cuisine_type": "cuisine type"
        }},
        // ... repeat for each meal type
    ]
}}"""

        return prompt


def build_single_meal_prompt(
    session: "SuggestionSession",
    meal_index: int,
    inspiration_recipe: Optional["RecipeSearchResult"] = None,
) -> str:
    """
    Build compact prompt for generating a single meal.
    Target: ~500 output tokens for fast generation.

    Args:
        session: User's session with preferences
        meal_index: Which meal (0, 1, 2) for variety
        inspiration_recipe: Optional Pinecone recipe as reference

    Returns:
        Compact prompt string
    """
    ingredients_list = session.ingredients[:8] if session.ingredients else []
    ingredients_str = ", ".join(ingredients_list) if ingredients_list else "common ingredients"

    # Inspiration context (only if high confidence)
    inspiration_ctx = ""
    if inspiration_recipe and inspiration_recipe.confidence_score >= 0.6:
        insp_ingredients = [
            ing.get("name", "") for ing in inspiration_recipe.ingredients[:4]
        ]
        inspiration_ctx = f"""
INSPIRATION (adapt to user's ingredients):
- {inspiration_recipe.name}: {', '.join(insp_ingredients)}...
"""

    # Identify protein ingredients for variety guidance
    protein_keywords = ["chicken", "beef", "pork", "fish", "salmon", "tuna", "shrimp", "tofu", "egg", "lamb", "turkey"]
    proteins_available = [ing for ing in ingredients_list if any(p in ing.lower() for p in protein_keywords)]

    # Variety hints based on index - encourage different proteins
    if len(proteins_available) > 1:
        # Rotate through available proteins
        suggested_protein = proteins_available[meal_index % len(proteins_available)]
        protein_hint = f"Feature {suggested_protein} as main protein"
    else:
        protein_hint = ""

    # Cooking style hints for variety (rotate per meal)
    style_hints = [
        "Asian-inspired with bold flavors",
        "Mediterranean with herbs and olive oil",
        "Classic homestyle comfort",
    ]

    # Naming style hints to avoid robotic names (rotate per meal)
    naming_hints = [
        "Herb-Crusted", "Golden", "Savory", "Zesty", "Garden-Fresh",
        "Honey-Glazed", "Garlic-Butter", "Pan-Seared", "Citrus", "Rustic",
    ]
    suggested_naming = naming_hints[meal_index % len(naming_hints)]

    constraints = []
    if hasattr(session, "allergies") and session.allergies:
        constraints.append(f"AVOID: {', '.join(session.allergies)}")
    if hasattr(session, "dietary_preferences") and session.dietary_preferences:
        constraints.append(f"DIETARY: {', '.join(session.dietary_preferences)}")

    constraints_str = "\n".join(constraints)

    # Build style section
    style_section = style_hints[meal_index % len(style_hints)]
    if protein_hint:
        style_section = f"{protein_hint}. {style_section}"

    return f"""Generate 1 {session.meal_type} meal (~{session.target_calories} cal, max {session.cooking_time_minutes} min cook time).

INGREDIENTS TO USE: {ingredients_str}
{constraints_str}
{inspiration_ctx}
STYLE: {style_section}
NAMING HINT: Consider "{suggested_naming}" style (e.g., "{suggested_naming} Chicken", "Garlic-Butter Steak")

REQUIRED JSON FORMAT:
{{
  "name": "Restaurant-Style Dish Name",
  "description": "Appetizing description that makes you hungry",
  "ingredients": [
    {{"name": "protein_from_list", "amount": 200, "unit": "g"}},
    {{"name": "carb_from_list", "amount": 100, "unit": "g"}},
    {{"name": "vegetable_from_list", "amount": 150, "unit": "g"}},
    {{"name": "olive oil", "amount": 1, "unit": "tbsp"}}
  ],
  "recipe_steps": [
    {{"step": 1, "instruction": "Prepare main ingredient", "duration_minutes": 2}},
    {{"step": 2, "instruction": "Heat oil in pan over medium-high heat", "duration_minutes": 1}},
    {{"step": 3, "instruction": "Cook protein until done", "duration_minutes": 8}},
    {{"step": 4, "instruction": "Combine and serve", "duration_minutes": 5}}
  ],
  "prep_time_minutes": 20
}}

STRICT RULES:
- Name should sound like a restaurant menu item (NOT "Speedy", "Quick", "Power Bowl")
- Description should be appetizing, not technical
- MUST use ingredients from INGREDIENTS TO USE list
- MUST include 4-6 ingredients with exact amounts
- MUST include 3-4 detailed recipe steps with duration
- Use specific quantities (g, ml, tbsp, tsp)
- NO calories/protein/carbs/fat fields
- Return ONLY valid JSON, no extra text"""
