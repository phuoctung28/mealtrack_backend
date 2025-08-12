"""
Domain service for generating prompts for meal generation.
"""
from typing import Dict, Any
from src.domain.model.meal_generation_request import MealGenerationContext, MealGenerationType
from src.domain.model.prompt_context import PromptContext
from src.domain.model.meal_plan import MealType


class PromptGenerationService:
    """Service for generating prompts based on meal generation context."""
    
    def generate_prompt_and_system_message(self, context: MealGenerationContext) -> tuple[str, str]:
        """Generate prompt and system message for the given context."""
        prompt_context = PromptContext(context)
        
        if context.request.generation_type == MealGenerationType.WEEKLY_INGREDIENT_BASED:
            return self._generate_weekly_ingredient_prompt(prompt_context)
        elif context.request.generation_type == MealGenerationType.DAILY_INGREDIENT_BASED:
            return self._generate_daily_ingredient_prompt(prompt_context)
        elif context.request.generation_type == MealGenerationType.DAILY_PROFILE_BASED:
            return self._generate_daily_profile_prompt(prompt_context)
        else:
            raise ValueError(f"Unsupported generation type: {context.request.generation_type}")
    
    def generate_single_meal_prompt(self, meal_type: MealType, calorie_target: int, context: MealGenerationContext) -> tuple[str, str]:
        """Generate prompt for a single meal."""
        prompt_context = PromptContext(context)
        
        if context.is_ingredient_based():
            return self._generate_single_ingredient_meal_prompt(meal_type, calorie_target, prompt_context)
        else:
            return self._generate_single_profile_meal_prompt(meal_type, calorie_target, prompt_context)
    
    def _generate_weekly_ingredient_prompt(self, context: PromptContext) -> tuple[str, str]:
        """Generate weekly ingredient-based meal plan prompt."""
        meals_per_day = len(context.generation_context.meal_types)
        
        # Create a more explicit schema
        schema = (
            '{\n'
            '  "week": [\n'
            '    {\n'
            '      "day": "Monday",\n'
            '      "meals": [\n'
            '        {\n'
            '          "meal_type": "breakfast",\n'
            '          "name": "Meal Name",\n'
            '          "description": "Brief description",\n'
            '          "calories": 400,\n'
            '          "protein": 25.0,\n'
            '          "carbs": 45.0,\n'
            '          "fat": 15.0,\n'
            '          "prep_time": 10,\n'
            '          "cook_time": 15,\n'
            '          "ingredients": ["ingredient1", "ingredient2"],\n'
            '          "instructions": ["step1", "step2"],\n'
            '          "is_vegetarian": true,\n'
            '          "is_vegan": false,\n'
            '          "is_gluten_free": false,\n'
            '          "cuisine_type": "International"\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  ]\n'
            '}'
        )
        
        snack_requirement = ""
        if context.generation_context.request.user_profile.include_snacks:
            snack_requirement = "\n6. Include 1 healthy snack per day."
        
        snack_text = " + 1 snack" if context.generation_context.request.user_profile.include_snacks else ""
        
        # Build detailed nutritional targets
        nutrition_targets = context.generation_context.request.nutrition_targets
        daily_targets = (
            f"DAILY NUTRITION TARGETS (must be met exactly each day):\n"
            f"- Calories: {nutrition_targets.calories}\n"
            f"- Protein: {nutrition_targets.protein}g\n"
            f"- Carbs: {nutrition_targets.carbs}g\n"
            f"- Fat: {nutrition_targets.fat}g\n"
        )
        
        # Build meal-specific targets
        meal_targets = []
        for meal_type in context.generation_context.meal_types:
            calorie_target = context.generation_context.calorie_distribution.get_calories_for_meal(meal_type)
            meal_percentage = calorie_target / nutrition_targets.calories
            protein_target = nutrition_targets.protein * meal_percentage
            carbs_target = nutrition_targets.carbs * meal_percentage
            fat_target = nutrition_targets.fat * meal_percentage
            
            meal_targets.append(
                f"- {meal_type.value.title()}: {calorie_target} cal, {protein_target:.1f}g protein, {carbs_target:.1f}g carbs, {fat_target:.1f}g fat"
            )
        
        meal_targets_text = "MEAL TARGETS PER DAY:\n" + "\n".join(meal_targets)
        
        week_dates = context.get_week_dates_text()
        prompt = (
            f"Generate a 7-day meal plan for {week_dates} using ONLY these ingredients.\n\n"
            f"Available Ingredients: {context.get_ingredients_text()}\n"
            f"Available Seasonings: {context.get_seasonings_text()}{context.get_dietary_requirements_text()}\n\n"
            f"{daily_targets}\n"
            f"{meal_targets_text}\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"- Generate exactly {meals_per_day} meals per day: {context.get_meal_types_text()}\n"
            f"- Use ONLY the listed ingredients above\n"
            f"- Each day must total EXACTLY {nutrition_targets.calories} calories, {nutrition_targets.protein}g protein, {nutrition_targets.carbs}g carbs, {nutrition_targets.fat}g fat\n"
            f"- Each meal must match its target nutrition values above\n"
            f"- Keep meal descriptions under 20 words\n"
            f"- Keep instructions to 3 steps maximum{snack_requirement}\n\n"
            f"CRITICAL: Return ONLY valid JSON in this exact format:\n{schema}\n\n"
            f"Generate all 7 days with precise nutrition matching the targets above."
        )
        
        return prompt, "You are a meal planning assistant. Return only valid JSON without any markdown formatting or explanations."
    
    def _generate_daily_ingredient_prompt(self, context: PromptContext) -> tuple[str, str]:
        """Generate daily ingredient-based meal plan prompt."""
        meals_per_day = len(context.generation_context.meal_types)
        
        # Create schema for daily meal plan
        schema = (
            '{\\n'
            '  "meals": [\\n'
            '    {\\n'
            '      "meal_type": "breakfast",\\n'
            '      "name": "Meal Name",\\n'
            '      "description": "Brief description",\\n'
            '      "calories": 400,\\n'
            '      "protein": 25.0,\\n'
            '      "carbs": 45.0,\\n'
            '      "fat": 15.0,\\n'
            '      "prep_time": 10,\\n'
            '      "cook_time": 15,\\n'
            '      "ingredients": ["ingredient1", "ingredient2"],\\n'
            '      "instructions": ["step1", "step2"],\\n'
            '      "is_vegetarian": true,\\n'
            '      "is_vegan": false,\\n'
            '      "is_gluten_free": false,\\n'
            '      "cuisine_type": "International"\\n'
            '    }\\n'
            '  ]\\n'
            '}'
        )
        
        snack_requirement = ""
        if context.generation_context.request.user_profile.include_snacks:
            snack_requirement = "\\n6. Include 1 healthy snack for the day."
        
        # Build detailed nutritional targets
        nutrition_targets = context.generation_context.request.nutrition_targets
        daily_targets = (
            f"DAILY NUTRITION TARGETS (must be met exactly):\\n"
            f"- Calories: {nutrition_targets.calories}\\n"
            f"- Protein: {nutrition_targets.protein}g\\n"
            f"- Carbs: {nutrition_targets.carbs}g\\n"
            f"- Fat: {nutrition_targets.fat}g\\n"
        )
        
        # Build meal-specific targets
        meal_targets = []
        for meal_type in context.generation_context.meal_types:
            calorie_target = context.generation_context.calorie_distribution.get_calories_for_meal(meal_type)
            meal_percentage = calorie_target / nutrition_targets.calories
            protein_target = nutrition_targets.protein * meal_percentage
            carbs_target = nutrition_targets.carbs * meal_percentage
            fat_target = nutrition_targets.fat * meal_percentage
            
            meal_targets.append(
                f"- {meal_type.value.title()}: {calorie_target} cal, {protein_target:.1f}g protein, {carbs_target:.1f}g carbs, {fat_target:.1f}g fat"
            )
        
        meal_targets_text = "MEAL TARGETS FOR TODAY:\\n" + "\\n".join(meal_targets)
        
        prompt = (
            f"Generate a daily meal plan using ONLY these ingredients.\\n\\n"
            f"Available Ingredients: {context.get_ingredients_text()}\\n"
            f"Available Seasonings: {context.get_seasonings_text()}{context.get_dietary_requirements_text()}\\n\\n"
            f"{daily_targets}\\n"
            f"{meal_targets_text}\\n\\n"
            f"CRITICAL REQUIREMENTS:\\n"
            f"- Generate exactly {meals_per_day} meals: {context.get_meal_types_text()}\\n"
            f"- Use ONLY the listed ingredients above\\n"
            f"- All meals must total EXACTLY {nutrition_targets.calories} calories, {nutrition_targets.protein}g protein, {nutrition_targets.carbs}g carbs, {nutrition_targets.fat}g fat\\n"
            f"- Each meal must match its target nutrition values above\\n"
            f"- Keep meal descriptions under 20 words\\n"
            f"- Keep instructions to 3 steps maximum{snack_requirement}\\n\\n"
            f"CRITICAL: Return ONLY valid JSON in this exact format:\\n{schema}\\n\\n"
            f"Generate all meals with precise nutrition matching the targets above."
        )
        
        return prompt, "You are a meal planning assistant. Return only valid JSON without any markdown formatting or explanations."
    
    def _generate_daily_profile_prompt(self, context: PromptContext) -> tuple[str, str]:
        """Generate daily profile-based meal plan prompt."""
        # Build meal targets string
        meal_targets = []
        for meal_type in context.generation_context.meal_types:
            calorie_target = context.generation_context.calorie_distribution.get_calories_for_meal(meal_type)
            meal_percentage = calorie_target / context.generation_context.request.nutrition_targets.calories
            
            # Calculate macro targets for this meal
            protein_target = context.generation_context.request.nutrition_targets.protein * meal_percentage
            carbs_target = context.generation_context.request.nutrition_targets.carbs * meal_percentage
            fat_target = context.generation_context.request.nutrition_targets.fat * meal_percentage
            
            meal_targets.append(f"""
{meal_type.value.title()}:
- Calories: {int(calorie_target)} (±50 calories)
- Protein: {int(protein_target)}g
- Carbs: {int(carbs_target)}g
- Fat: {int(fat_target)}g""")
        
        meal_targets_str = "\n".join(meal_targets)
        
        profile = context.generation_context.request.user_profile
        dietary_str = ", ".join(profile.dietary_preferences) if profile.dietary_preferences else "none"
        health_str = ", ".join(profile.health_conditions) if profile.health_conditions else "none"
        
        prompt = f"""Generate a complete daily meal plan with these requirements:

User Profile:
- Fitness Goal: {profile.fitness_goal} - {context.get_goal_guidance()}
- Activity Level: {profile.activity_level}
- Dietary Restrictions: {dietary_str}
- Health Conditions: {health_str}
- Total Daily Calories: {context.generation_context.request.nutrition_targets.calories}

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
        
        return prompt, "You are a professional nutritionist creating personalized daily meal plans."
    
    def _generate_single_ingredient_meal_prompt(self, meal_type: MealType, calorie_target: int, context: PromptContext) -> tuple[str, str]:
        """Generate prompt for a single ingredient-based meal."""
        prompt = f"""Create a {meal_type.value} recipe using these available ingredients: {context.get_ingredients_text()}
Available seasonings: {context.get_seasonings_text()}
Target calories: {calorie_target}

IMPORTANT: Only use the ingredients listed above. Do not add any other ingredients.
{context.get_dietary_requirements_text()}{context.get_allergy_restrictions_text()}

Create a simple, practical recipe that:
- Uses ONLY the available ingredients listed above
- Creates a balanced and nutritious {meal_type.value}
- Is easy to prepare
- CRITICAL: NEVER use any ingredients that match the allergies listed above

Respond with valid JSON only:
{{
    "name": "Recipe Name",
    "description": "Brief description",
    "calories": {calorie_target},
    "protein": 25.0,
    "carbs": 35.0,
    "fat": 15.0,
    "prep_time": 15,
    "cook_time": 20,
    "ingredients": ["chicken", "broccoli", "rice"],
    "instructions": ["step 1", "step 2"],
    "is_vegetarian": false,
    "is_vegan": false,
    "is_gluten_free": true,
    "cuisine_type": "International"
}}"""
        
        return prompt, "You are a professional nutritionist creating personalized meal suggestions."
    
    def _generate_single_profile_meal_prompt(self, meal_type: MealType, calorie_target: int, context: PromptContext) -> tuple[str, str]:
        """Generate prompt for a single profile-based meal."""
        profile = context.generation_context.request.user_profile
        
        # Calculate macro targets for this meal
        meal_percentage = calorie_target / context.generation_context.request.nutrition_targets.calories
        protein_target = context.generation_context.request.nutrition_targets.protein * meal_percentage
        carbs_target = context.generation_context.request.nutrition_targets.carbs * meal_percentage
        fat_target = context.generation_context.request.nutrition_targets.fat * meal_percentage
        
        dietary_str = ", ".join(profile.dietary_preferences) if profile.dietary_preferences else "none"
        health_str = ", ".join(profile.health_conditions) if profile.health_conditions else "none"
        
        prompt = f"""Generate a {meal_type.value} meal suggestion with these requirements:

User Profile:
- Fitness Goal: {profile.fitness_goal} - {context.get_goal_guidance()}
- Activity Level: {profile.activity_level}
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
        
        return prompt, "You are a professional nutritionist creating personalized meal suggestions."