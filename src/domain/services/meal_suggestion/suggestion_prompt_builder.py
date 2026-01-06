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
        inspiration_recipe: Optional (DEPRECATED - not used)

    Returns:
        Compact prompt string
    """
    ingredients_list = session.ingredients[:8] if session.ingredients else []
    ingredients_str = ", ".join(ingredients_list) if ingredients_list else "common ingredients"

    # REMOVED: Pinecone inspiration (using pure AI prompts for variety instead)

    # Identify protein ingredients for variety guidance
    protein_keywords = ["chicken", "beef", "pork", "fish", "salmon", "tuna", "shrimp", "tofu", "egg", "lamb", "turkey"]
    proteins_available = [ing for ing in ingredients_list if any(p in ing.lower() for p in protein_keywords)]

    # Subtle variety through protein rotation (if multiple proteins available)
    protein_hint = ""
    if len(proteins_available) > 1:
        suggested_protein = proteins_available[meal_index % len(proteins_available)]
        protein_hint = f"Consider featuring {suggested_protein} as the main protein"

    # REMOVED: Style hints (Asian, Mediterranean, etc.) - creates bias
    # REMOVED: Naming hints (Herb-Crusted, Golden, etc.) - creates repetitive patterns

    constraints = []
    if hasattr(session, "allergies") and session.allergies:
        constraints.append(f"⚠️ MUST AVOID: {', '.join(session.allergies)}")
    if hasattr(session, "dietary_preferences") and session.dietary_preferences:
        constraints.append(f"Dietary preferences: {', '.join(session.dietary_preferences)}")

    constraints_str = "\n".join(constraints) if constraints else ""

    return f"""Generate 1 complete {session.meal_type} meal (~{session.target_calories} cal, ≤{session.cooking_time_minutes}min).

INGREDIENTS: {ingredients_str}
{constraints_str}
{protein_hint}

OUTPUT (compact JSON, no whitespace):
{{
  "name": "Dish Name",
  "description": "Brief appetizing description",
  "ingredients": [
    {{"name": "ingredient1", "amount": 200, "unit": "g"}},
    {{"name": "ingredient2", "amount": 100, "unit": "g"}},
    {{"name": "ingredient3", "amount": 150, "unit": "g"}},
    {{"name": "ingredient4", "amount": 1, "unit": "tbsp"}}
  ],
  "recipe_steps": [
    {{"step": 1, "instruction": "Action", "duration_minutes": 5}},
    {{"step": 2, "instruction": "Action", "duration_minutes": 10}},
    {{"step": 3, "instruction": "Action", "duration_minutes": 8}}
  ],
  "prep_time_minutes": 20
}}

CRITICAL RULES:
1. MUST include ALL fields: name, description, ingredients (4-6 items), recipe_steps (3-4 steps), prep_time_minutes
2. MUST complete entire JSON - do NOT truncate
3. Name: Natural dish name (NOT "Quick/Speedy/Power Bowl"). Examples: "Garlic Butter Salmon", "Herb Chicken", "Spicy Beef"
4. Ingredients: Use from INGREDIENTS list, exact amounts (g/ml/tbsp/tsp)
5. Recipe steps: Clear instructions with duration_minutes
6. Return ONLY valid JSON, no markdown/extra text
7. NO calories/protein/carbs/fat fields

⚠️ COMPLETE THE ENTIRE JSON BEFORE STOPPING - all arrays must close properly!

"""


def build_meal_names_prompt(
    session: "SuggestionSession",
) -> str:
    """
    Phase 1: Generate 3 diverse meal names only (with structured output schema).
    
    Args:
        session: User's session with preferences
        
    Returns:
        Prompt for generating 3 meal names
    """
    ingredients_list = session.ingredients[:6] if session.ingredients else []
    ingredients_str = ", ".join(ingredients_list) if ingredients_list else "any ingredients"
    
    constraints = []
    if hasattr(session, "allergies") and session.allergies:
        constraints.append(f"⚠️ AVOID: {', '.join(session.allergies)}")
    if hasattr(session, "dietary_preferences") and session.dietary_preferences:
        constraints.append(f"Diet: {', '.join(session.dietary_preferences)}")
    
    constraints_str = " | " + " | ".join(constraints) if constraints else ""
    
    return f"""Generate exactly 3 VERY DIFFERENT {session.meal_type} meal names.

Ingredients: {ingredients_str}{constraints_str}

Requirements:
- Each meal must use different cuisine/flavor profile (Asian, Mediterranean, Latin, American, etc.)
- Each meal must use different cooking method (stir-fry, roasted, grilled, pan-seared, baked, etc.)
- Use proteins/ingredients from the list above
- Natural, appetizing names (NOT "Quick", "Speedy", "Power Bowl", "Healthy Bowl")
- KEEP NAMES CONCISE (max 6-7 words, ~50 chars)
- Good examples: "Spicy Thai Basil Chicken", "Honey-Glazed Salmon", "Herb-Roasted Pork"
- Bad examples: "Spicy Gochujang Chicken and Broccoli Stir-fry with Steamed Jasmine Rice" (too long!)

⚠️ CRITICAL: Generate 3 DISTINCTLY DIFFERENT, CONCISE meals with unique flavors!

"""


def build_recipe_details_prompt(
    meal_name: str,
    session: "SuggestionSession",
) -> str:
    """
    Phase 2: Generate full recipe details for a specific meal name (with structured output schema).
    
    Args:
        meal_name: The meal name to generate recipe for
        session: User's session with preferences
        
    Returns:
        Prompt for generating recipe details
    """
    ingredients_list = session.ingredients[:6] if session.ingredients else []
    ingredients_str = ", ".join(ingredients_list) if ingredients_list else "any ingredients"
    
    constraints_parts = []
    if hasattr(session, "allergies") and session.allergies:
        constraints_parts.append(f"⚠️ AVOID: {', '.join(session.allergies)}")
    if hasattr(session, "dietary_preferences") and session.dietary_preferences:
        constraints_parts.append(f"Diet: {', '.join(session.dietary_preferences)}")
    
    constraints_str = " | ".join(constraints_parts) if constraints_parts else ""
    
    return f"""Generate complete recipe details for: "{meal_name}"

Available ingredients: {ingredients_str}{' | ' + constraints_str if constraints_str else ''}
Target: ~{session.target_calories} calories | ≤{session.cooking_time_minutes} minutes cooking time

CRITICAL - Portion Sizing:
- This meal should be approximately {session.target_calories} calories total
- Use APPROPRIATE portion sizes (e.g., for 800 cal lunch: ~200g protein, ~150g carbs, ~100g vegetables)
- For lower calorie targets (<600 cal), use smaller portions (e.g., 150g protein, 100g carbs)
- For higher calorie targets (>1000 cal), use larger portions (e.g., 300g protein, 200g carbs)

Requirements:
- Recipe must match the meal name "{meal_name}" exactly
- Use 4-6 ingredients from the available list with specific amounts (g, ml, tbsp, tsp)
- Provide 3-4 clear, actionable recipe steps with duration for each step
- Description should highlight the meal's key flavors and appeal
- Total prep_time_minutes must be ≤{session.cooking_time_minutes}

NOTE: Do NOT include nutrition data in response - backend calculates it automatically.

"""
