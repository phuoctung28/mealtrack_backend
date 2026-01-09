import json
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.domain.model.meal_planning import (
    MealPlan, PlannedMeal, DayPlan, UserPreferences,
    FitnessGoal, MealType, PlanDuration
)
from src.infra.services.ai.gemini_model_manager import GeminiModelManager

logger = logging.getLogger(__name__)


class MealPlanService:
    """Service for generating and managing meal plans using AI"""
    
    def __init__(self):
        self._model_manager = GeminiModelManager.get_instance()
        self._model = None  # Lazy load
        
    @property
    def model(self):
        """Lazy load the ChatGoogleGenerativeAI model using singleton manager."""
        if self._model is None:
            # Use standard temperature=0.7 to share model instance across all services
            self._model = self._model_manager.get_model()
        return self._model
    
    def generate_meal_plan(self, user_id: str, preferences: UserPreferences) -> MealPlan:
        """Generate a complete meal plan based on user preferences"""
        logger.info(f"Generating meal plan for user {user_id}")
        
        # Determine number of days
        num_days = 7 if preferences.plan_duration == PlanDuration.WEEKLY else 1
        start_date = date.today()
        
        # Generate meals for each day
        days = []
        for i in range(num_days):
            current_date = start_date + timedelta(days=i)
            is_weekend = current_date.weekday() >= 5
            
            day_meals = self._generate_day_meals(
                preferences=preferences,
                is_weekend=is_weekend
            )
            
            days.append(DayPlan(date=current_date, meals=day_meals))
        
        # Create and return meal plan
        meal_plan = MealPlan(
            user_id=user_id,
            preferences=preferences,
            days=days
        )
        
        logger.info(f"Generated meal plan {meal_plan.plan_id} with {len(days)} days")
        return meal_plan
    
    def _generate_day_meals(self, preferences: UserPreferences, is_weekend: bool) -> List[PlannedMeal]:
        """Generate meals for a single day"""
        meals = []
        
        # Determine cooking time based on day type
        max_cooking_time = preferences.cooking_time_weekend if is_weekend else preferences.cooking_time_weekday
        
        # Generate main meals
        for i in range(preferences.meals_per_day):
            if i == 0:
                meal_type = MealType.BREAKFAST
            elif i == 1:
                meal_type = MealType.LUNCH
            elif i == 2:
                meal_type = MealType.DINNER
            else:
                meal_type = MealType.LUNCH  # Extra meals default to lunch type
            
            meal = self._generate_single_meal(
                meal_type=meal_type,
                preferences=preferences,
                max_cooking_time=max_cooking_time
            )
            meals.append(meal)
        
        # Generate snacks
        for i in range(preferences.snacks_per_day):
            snack = self._generate_single_meal(
                meal_type=MealType.SNACK,
                preferences=preferences,
                max_cooking_time=15  # Snacks should be quick
            )
            meals.append(snack)
        
        return meals
    
    def _generate_single_meal(self, meal_type: MealType, preferences: UserPreferences, 
                             max_cooking_time: int) -> PlannedMeal:
        """Generate a single meal using Google Gemini AI"""
        
        prompt = self._build_meal_generation_prompt(meal_type, preferences, max_cooking_time)
        
        try:
            messages = [
                SystemMessage(content="You are a professional meal planning assistant that always returns valid JSON."),
                HumanMessage(content=prompt)
            ]
            
            response = self.model.invoke(messages)
            content = response.content
            
            # Extract JSON from the response
            try:
                # Try to parse the entire response as JSON
                meal_data = json.loads(content)
            except json.JSONDecodeError:
                # If that fails, try to find and extract just the JSON part
                import re
                json_match = re.search(r'```json(.*?)```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                    meal_data = json.loads(json_str)
                else:
                    # As a last resort, try to find any JSON-like structure
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        meal_data = json.loads(json_str)
                    else:
                        raise ValueError("Could not extract JSON from response")
            
            return PlannedMeal(
                meal_type=meal_type,
                name=meal_data["name"],
                description=meal_data["description"],
                prep_time=meal_data["prep_time"],
                cook_time=meal_data["cook_time"],
                calories=meal_data["calories"],
                protein=meal_data["protein"],
                carbs=meal_data["carbs"],
                fat=meal_data["fat"],
                ingredients=meal_data["ingredients"],
                instructions=meal_data["instructions"],
                is_vegetarian=meal_data.get("is_vegetarian", False),
                is_vegan=meal_data.get("is_vegan", False),
                is_gluten_free=meal_data.get("is_gluten_free", False),
                cuisine_type=meal_data.get("cuisine_type")
            )
            
        except Exception as e:
            logger.error(f"Error generating meal: {str(e)}")
            # Return a fallback meal
            return self._get_fallback_meal(meal_type)
    
    def _build_meal_generation_prompt(self, meal_type: MealType, preferences: UserPreferences, 
                                    max_cooking_time: int) -> str:
        """Build prompt for meal generation"""
        
        dietary_str = ", ".join([pref.value for pref in preferences.dietary_preferences])
        cuisines_str = ", ".join(preferences.favorite_cuisines) if preferences.favorite_cuisines else "any"
        disliked_str = ", ".join(preferences.disliked_ingredients) if preferences.disliked_ingredients else "none"
        allergies_str = ", ".join(preferences.allergies) if preferences.allergies else "none"
        
        fitness_goals = {
            FitnessGoal.BULK: "high protein (30-40g), moderate carbs, healthy fats",
            FitnessGoal.CUT: "moderate protein, lower carbs, controlled calories (300-500 for meals, 100-200 for snacks)",
            FitnessGoal.RECOMP: "balanced macros with high protein, appropriate portions"
        }
        
        nutrition_guidance = fitness_goals.get(preferences.fitness_goal, "balanced nutrition")
        
        prompt = f"""Generate a {meal_type.value} recipe with the following requirements:

Dietary Preferences: {dietary_str}
Allergies to avoid: {allergies_str}
Fitness Goal: {preferences.fitness_goal.value} - ensure {nutrition_guidance}
Maximum total cooking time: {max_cooking_time} minutes
Preferred cuisines: {cuisines_str}
Ingredients to avoid: {disliked_str}

Return ONLY a JSON object with this exact structure:
{{
    "name": "Recipe name",
    "description": "Brief appetizing description",
    "prep_time": 10,
    "cook_time": 20,
    "calories": 400,
    "protein": 25.5,
    "carbs": 35.2,
    "fat": 15.8,
    "ingredients": ["ingredient 1", "ingredient 2"],
    "instructions": ["Step 1", "Step 2"],
    "is_vegetarian": true/false,
    "is_vegan": true/false,
    "is_gluten_free": true/false,
    "cuisine_type": "Italian/Asian/Mexican/etc"
}}

Ensure the recipe is practical, delicious, and meets all dietary requirements."""
        
        return prompt
    
    def _get_fallback_meal(self, meal_type: MealType) -> PlannedMeal:
        """Return a simple fallback meal if AI generation fails"""
        fallback_meals = {
            MealType.BREAKFAST: {
                "name": "Greek Yogurt Parfait",
                "description": "Quick and healthy breakfast with berries and nuts",
                "prep_time": 5,
                "cook_time": 0,
                "calories": 300,
                "protein": 20,
                "carbs": 35,
                "fat": 10,
                "ingredients": ["Greek yogurt", "Mixed berries", "Granola", "Honey"],
                "instructions": ["Layer yogurt in a bowl", "Add berries", "Top with granola", "Drizzle with honey"],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": False
            },
            MealType.LUNCH: {
                "name": "Quinoa Buddha Bowl",
                "description": "Nutritious bowl with quinoa, vegetables, and protein",
                "prep_time": 15,
                "cook_time": 20,
                "calories": 450,
                "protein": 18,
                "carbs": 55,
                "fat": 15,
                "ingredients": ["Quinoa", "Chickpeas", "Mixed vegetables", "Tahini dressing"],
                "instructions": ["Cook quinoa", "Roast vegetables", "Prepare chickpeas", "Assemble bowl", "Add dressing"],
                "is_vegetarian": True,
                "is_vegan": True,
                "is_gluten_free": True
            },
            MealType.DINNER: {
                "name": "Grilled Chicken with Vegetables",
                "description": "Simple grilled chicken with roasted seasonal vegetables",
                "prep_time": 10,
                "cook_time": 25,
                "calories": 400,
                "protein": 35,
                "carbs": 30,
                "fat": 12,
                "ingredients": ["Chicken breast", "Broccoli", "Carrots", "Olive oil", "Herbs"],
                "instructions": ["Season chicken", "Grill chicken", "Roast vegetables", "Serve together"],
                "is_vegetarian": False,
                "is_vegan": False,
                "is_gluten_free": True
            },
            MealType.SNACK: {
                "name": "Apple with Almond Butter",
                "description": "Quick and satisfying snack",
                "prep_time": 2,
                "cook_time": 0,
                "calories": 200,
                "protein": 7,
                "carbs": 25,
                "fat": 10,
                "ingredients": ["Apple", "Almond butter"],
                "instructions": ["Slice apple", "Serve with almond butter"],
                "is_vegetarian": True,
                "is_vegan": True,
                "is_gluten_free": True
            }
        }
        
        meal_data = fallback_meals.get(meal_type, fallback_meals[MealType.LUNCH])
        return PlannedMeal(meal_type=meal_type, **meal_data)
    
    def regenerate_meal(self, meal_plan: MealPlan, date: date, meal_id: str, 
                       additional_preferences: Optional[Dict] = None) -> PlannedMeal:
        """Regenerate a specific meal with optional additional preferences"""
        
        # Find the meal to replace
        day_plan = meal_plan.get_day(date)
        if not day_plan:
            raise ValueError(f"No meal plan found for date {date}")
        
        old_meal = None
        for meal in day_plan.meals:
            if meal.meal_id == meal_id:
                old_meal = meal
                break
        
        if not old_meal:
            raise ValueError(f"Meal {meal_id} not found in plan")
        
        # Generate new meal with same type
        is_weekend = date.weekday() >= 5
        max_cooking_time = (meal_plan.preferences.cooking_time_weekend if is_weekend 
                          else meal_plan.preferences.cooking_time_weekday)
        
        # Create modified preferences if additional preferences provided
        preferences = meal_plan.preferences
        if additional_preferences:
            # This is a simplified approach - in production, properly merge preferences
            pass
        
        new_meal = self._generate_single_meal(
            meal_type=old_meal.meal_type,
            preferences=preferences,
            max_cooking_time=max_cooking_time
        )
        
        # Replace in meal plan
        meal_plan.replace_meal(date, meal_id, new_meal)
        
        return new_meal