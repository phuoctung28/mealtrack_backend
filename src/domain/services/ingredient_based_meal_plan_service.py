"""
Simplified ingredient-based meal plan service.
Just generates meal recommendations based on available ingredients - no quantity tracking.
"""
import json
import logging
import re
from datetime import date
from typing import Dict, Any, List

from langchain_google_genai import ChatGoogleGenerativeAI

from src.domain.model.meal_plan import PlannedMeal, MealType

logger = logging.getLogger(__name__)


def _determine_meal_types(meals_per_day: int, include_snacks: bool) -> List[MealType]:
    """Determine what meal types to generate."""
    meal_types = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER]

    # Add additional meals if requested
    if meals_per_day > 3:
        for i in range(meals_per_day - 3):
            meal_types.append(MealType.SNACK)

    # Add snacks if specifically requested
    if include_snacks and MealType.SNACK not in meal_types:
        meal_types.append(MealType.SNACK)

    return meal_types


def _calculate_calorie_distribution(request_data: Dict[str, Any], meal_types: List[MealType]) -> Dict[MealType, int]:
    """Calculate simple calorie distribution for the meal plan."""
    target_calories = request_data.get('target_calories') or 1800

    # Standard distribution ratios
    breakfast_ratio = 0.25
    lunch_ratio = 0.35
    dinner_ratio = 0.40
    snack_ratio = 0.10

    num_snacks = sum(1 for mt in meal_types if mt == MealType.SNACK)

    # Reserve calories for snacks
    snack_calories_per_snack = int(target_calories * snack_ratio) if num_snacks > 0 else 0
    remaining_calories = target_calories - (num_snacks * snack_calories_per_snack)

    calorie_distribution = {}

    for meal_type in meal_types:
        if meal_type == MealType.SNACK:
            calorie_distribution[meal_type] = snack_calories_per_snack
        elif meal_type == MealType.BREAKFAST:
            calorie_distribution[meal_type] = int(remaining_calories * breakfast_ratio)
        elif meal_type == MealType.LUNCH:
            calorie_distribution[meal_type] = int(remaining_calories * lunch_ratio)
        elif meal_type == MealType.DINNER:
            calorie_distribution[meal_type] = int(remaining_calories * dinner_ratio)
        else:
            # Default for any other meal types
            calorie_distribution[meal_type] = int(remaining_calories / 3)

    return calorie_distribution


class IngredientBasedMealPlanService:
    """Simplified service for generating meal plans based on available ingredients."""
    
    def __init__(self):
        import os
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        if not google_api_key:
            logger.warning("GOOGLE_API_KEY not found. AI meal generation will use fallback meals.")
            self.llm = None
        else:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.3,
                max_tokens=2000,
                timeout=30,
                google_api_key=google_api_key
            )
    
    def generate_ingredient_based_meal_plan(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a simple meal plan based on available ingredients.
        
        Args:
            request_data: Dictionary containing user info and available ingredients
            
        Returns:
            Complete meal plan response
        """
        logger.info(f"Generating simple ingredient-based meal plan for user {request_data.get('user_id')}")
        
        # Extract key parameters
        user_id = request_data.get('user_id', 'unknown')
        meals_per_day = request_data.get('meals_per_day') or 3
        plan_date = request_data.get('plan_date') or date.today().isoformat()
        
        # Determine meal types
        meal_types = _determine_meal_types(meals_per_day, request_data.get('include_snacks', False))
        
        # Calculate calorie distribution
        calorie_distribution = _calculate_calorie_distribution(request_data, meal_types)
        
        # Generate meals
        formatted_meals = []
        total_calories = 0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        
        for meal_type in meal_types:
            calorie_target = calorie_distribution[meal_type]
            
            try:
                # Generate meal using AI
                meal = self._generate_simple_meal(meal_type, calorie_target, request_data)
                
                # Format meal for response
                meal_dict = {
                    "meal_id": meal.meal_id,
                    "meal_type": meal_type.value,
                    "name": meal.name,
                    "description": meal.description,
                    "prep_time": meal.prep_time,
                    "cook_time": meal.cook_time,
                    "total_time": meal.prep_time + meal.cook_time,
                    "calories": meal.calories,
                    "protein": meal.protein,
                    "carbs": meal.carbs,
                    "fat": meal.fat,
                    "ingredients": meal.ingredients,
                    "instructions": meal.instructions,
                    "is_vegetarian": meal.is_vegetarian,
                    "is_vegan": meal.is_vegan,
                    "is_gluten_free": meal.is_gluten_free,
                    "cuisine_type": meal.cuisine_type
                }
                formatted_meals.append(meal_dict)
                
                # Add to totals
                total_calories += meal.calories
                total_protein += meal.protein
                total_carbs += meal.carbs
                total_fat += meal.fat
                
            except Exception as e:
                logger.error(f"Error generating {meal_type.value} meal: {str(e)}")
                # Use fallback meal
                allergies = request_data.get('allergies', [])
                fallback_meal = self._get_fallback_meal(meal_type, calorie_target, allergies)
                meal_dict = {
                    "meal_id": fallback_meal.meal_id,
                    "meal_type": meal_type.value,
                    "name": fallback_meal.name,
                    "description": fallback_meal.description,
                    "prep_time": fallback_meal.prep_time,
                    "cook_time": fallback_meal.cook_time,
                    "total_time": fallback_meal.prep_time + fallback_meal.cook_time,
                    "calories": fallback_meal.calories,
                    "protein": fallback_meal.protein,
                    "carbs": fallback_meal.carbs,
                    "fat": fallback_meal.fat,
                    "ingredients": fallback_meal.ingredients,
                    "instructions": fallback_meal.instructions,
                    "is_vegetarian": fallback_meal.is_vegetarian,
                    "is_vegan": fallback_meal.is_vegan,
                    "is_gluten_free": fallback_meal.is_gluten_free,
                    "cuisine_type": fallback_meal.cuisine_type
                }
                formatted_meals.append(meal_dict)
                
                total_calories += fallback_meal.calories
                total_protein += fallback_meal.protein
                total_carbs += fallback_meal.carbs
                total_fat += fallback_meal.fat
        
        # Create target nutrition with all required fields
        target_nutrition = {
            "calories": request_data.get('target_calories') or 1800,
            "protein": request_data.get('target_protein') or 120.0,
            "carbs": request_data.get('target_carbs') or 200.0,
            "fat": request_data.get('target_fat') or 80.0
        }
        
        # Build simple response
        return {
            "user_id": user_id,
            "date": plan_date,
            "meals": formatted_meals,
            "total_nutrition": {
                "calories": int(total_calories),
                "protein": round(total_protein, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1)
            },
            "target_nutrition": target_nutrition,
            "user_preferences": {
                "dietary_preferences": request_data.get('dietary_preferences', []),
                "health_conditions": request_data.get('allergies', []),
                "allergies": request_data.get('allergies', []),
                "activity_level": "moderate",
                "fitness_goal": "maintenance",
                "meals_per_day": request_data.get('meals_per_day', 3),
                "snacks_per_day": 1 if request_data.get('include_snacks', False) else 0
            }
        }

    def _generate_simple_meal(self, meal_type: MealType, calorie_target: int, request_data: Dict[str, Any]) -> PlannedMeal:
        """Generate a simple meal using available ingredients."""
        
        # Build simple prompt
        prompt = self._build_simple_prompt(meal_type, calorie_target, request_data)
        
        # Get response from AI
        response = self.llm.invoke(prompt)
        content = response.content
        
        # Extract JSON from response
        meal_data = self._extract_json(content)
        
        # Create PlannedMeal object
        return PlannedMeal(
            meal_id=f"meal_{meal_type.value}_{hash(content) % 10000}",
            meal_type=meal_type,
            name=meal_data.get("name", f"Simple {meal_type.value.title()}"),
            description=meal_data.get("description", f"A nutritious {meal_type.value}"),
            calories=meal_data.get("calories", calorie_target),
            protein=meal_data.get("protein", 20.0),
            carbs=meal_data.get("carbs", 30.0),
            fat=meal_data.get("fat", 15.0),
            prep_time=meal_data.get("prep_time", 15),
            cook_time=meal_data.get("cook_time", 20),
            ingredients=meal_data.get("ingredients", ["Basic ingredients"]),
            instructions=meal_data.get("instructions", ["Prepare and cook as desired"]),
            is_vegetarian=meal_data.get("is_vegetarian", False),
            is_vegan=meal_data.get("is_vegan", False),
            is_gluten_free=meal_data.get("is_gluten_free", False),
            cuisine_type=meal_data.get("cuisine_type", "International")
        )
    
    def _build_simple_prompt(self, meal_type: MealType, calorie_target: int, request_data: Dict[str, Any]) -> str:
        """Build a simple prompt for meal generation."""
        
        available_ingredients = request_data.get('available_ingredients', [])
        available_seasonings = request_data.get('available_seasonings', [])
        dietary_preferences = request_data.get('dietary_preferences', [])
        allergies = request_data.get('allergies', [])
        
        # Format ingredients list
        ingredients_text = ", ".join(available_ingredients)
        seasonings_text = ", ".join(available_seasonings) if available_seasonings else "basic seasonings"
        
        prompt = f"""Create a {meal_type.value} recipe using these available ingredients: {ingredients_text}
Available seasonings: {seasonings_text}
Target calories: {calorie_target}

IMPORTANT: Only use the ingredients listed above. Do not add any other ingredients.
"""
        
        if dietary_preferences:
            prompt += f"Dietary preferences: {', '.join(dietary_preferences)}\n"
        
        if allergies:
            prompt += f"Allergies to avoid: {', '.join(allergies)}\n"
        
        prompt += f"""
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
        
        return prompt
    
    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from AI response."""
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # If no valid JSON found, raise error
        raise ValueError(f"Could not extract valid JSON from response: {content}")