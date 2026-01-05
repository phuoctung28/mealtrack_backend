"""
Prompt for generating meal suggestions.
"""
from typing import List, Optional


def generate_meal_suggestion_prompt(
    meal_type: str,
    calorie_target: int,
    ingredients: List[str],
    time_available_minutes: Optional[int],
    dietary_preferences: List[str],
    exclude_names: List[str]
) -> tuple[str, str]:
    """
    Generate prompt for creating exactly 3 meal suggestions.
    
    Args:
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        calorie_target: Target calories for the meal
        ingredients: Available ingredients
        time_available_minutes: Time constraint in minutes
        dietary_preferences: Dietary preferences
        exclude_names: Meal names to exclude (for regeneration)
    
    Returns:
        Tuple of (prompt, system_message)
    """
    
    # Build system message
    system_message = """You are a professional nutritionist and chef assistant.
Generate exactly 3 meal suggestions based on the user's requirements.
Each suggestion should be realistic, nutritious, and delicious.
Return ONLY valid JSON with no additional text or markdown formatting."""
    
    # Build user prompt
    prompt_parts = [
        f"Generate exactly 3 different {meal_type} meal suggestions with the following requirements:",
        f"\n**Target Calories per Meal:** {calorie_target} calories (±50 calories is acceptable)",
    ]
    
    # Add ingredients constraint
    if ingredients:
        ingredients_str = ", ".join(ingredients)
        prompt_parts.append(f"\n**Available Ingredients:** {ingredients_str}")
        prompt_parts.append("Try to use these ingredients, but you can add common pantry items.")
    
    # Add time constraint
    if time_available_minutes:
        prompt_parts.append(f"\n**Time Constraint:** Total cooking time (prep + cook) must be ≤ {time_available_minutes} minutes")
    
    # Add dietary preferences
    if dietary_preferences:
        prefs_str = ", ".join(dietary_preferences)
        prompt_parts.append(f"\n**Dietary Preferences:** {prefs_str}")
    
    # Add exclusion list
    if exclude_names:
        exclude_str = ", ".join(exclude_names)
        prompt_parts.append(f"\n**Exclude these meals (already suggested):** {exclude_str}")
        prompt_parts.append("Generate completely different meals from these.")
    
    # Add output format requirements
    prompt_parts.append("""

**Output Format:**
Return a JSON object with this exact structure:
{
  "suggestions": [
    {
      "name": "Meal Name",
      "description": "Brief appetizing description (1-2 sentences)",
      "prep_time": 10,
      "cook_time": 15,
      "calories": 520,
      "protein": 35.0,
      "carbs": 45.0,
      "fat": 18.0,
      "ingredients": ["ingredient with portion", "another ingredient with portion"],
      "seasonings": ["seasoning 1", "seasoning 2"],
      "instructions": ["Step 1", "Step 2", "Step 3"],
      "is_vegetarian": false,
      "is_vegan": false,
      "is_gluten_free": false,
      "cuisine_type": "Italian"
    }
  ]
}

**Important Requirements:**
1. Generate EXACTLY 3 suggestions in the "suggestions" array
2. Each meal should be unique and different from the others
3. Include specific portions for ingredients (e.g., "200g chicken breast", "1 cup rice")
4. Ensure prep_time + cook_time meets the time constraint if specified
5. Calories should be close to the target (within ±50 calories)
6. Macros (protein, carbs, fat) should be realistic and add up correctly
7. Instructions should be clear and actionable
8. Set dietary flags (is_vegetarian, is_vegan, is_gluten_free) accurately
9. Specify cuisine_type (e.g., Italian, Asian, Mexican, American, Mediterranean)
""")
    
    prompt = "".join(prompt_parts)
    
    return prompt, system_message


