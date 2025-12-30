import json
import logging
import os
import re
from typing import List, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.domain.model.meal_planning import PlannedMeal, MealType
from src.domain.model.meal_planning import SimpleMacroTargets

logger = logging.getLogger(__name__)


class DailyMealSuggestionService:
    """Service for generating daily meal suggestions based on user preferences from onboarding"""
    
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        self.model = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0.7,
            max_output_tokens=4000,  # Increased for multiple meals
            google_api_key=self.google_api_key,
            convert_system_message_to_human=True
        )
    
    def generate_daily_suggestions(self, user_preferences: Dict) -> List[PlannedMeal]:
        """
        Generate 3-5 meal suggestions for a day based on user onboarding data
        
        Args:
            user_preferences: Dictionary containing user data from onboarding
                - age, gender, height, weight
                - activity_level: sedentary/lightly_active/moderately_active/very_active/extra_active
                - goal: lose_weight/maintain_weight/gain_weight/build_muscle
                - dietary_preferences: List of dietary restrictions
                - health_conditions: List of health conditions
                - target_calories: Daily calorie target
                - target_macros: Daily macro targets (protein, carbs, fat)
        
        Returns:
            List of 3-5 PlannedMeal objects
        """
        logger.info(f"Generating daily meal suggestions for user preferences")
        
        # Use the new unified generation method
        return self._generate_all_meals_unified(user_preferences)
    
    def _generate_all_meals_unified(self, user_preferences: Dict) -> List[PlannedMeal]:
        """Generate all daily meals in a single request"""
        
        # Determine meal distribution based on calories
        target_calories = user_preferences.get('target_calories')
        if not target_calories:
            raise ValueError("target_calories is required for meal suggestions. Please provide user's calculated TDEE.")
        meal_distribution = self._calculate_meal_distribution(target_calories)
        
        # Build unified prompt for all meals
        prompt = self._build_unified_meal_prompt(meal_distribution, user_preferences)
        
        try:
            messages = [
                SystemMessage(content="You are a professional nutritionist creating personalized daily meal plans."),
                HumanMessage(content=prompt)
            ]
            
            response = self.model.invoke(messages)
            content = response.content
            
            # Extract JSON from response
            daily_meals_data = self._extract_unified_meals_json(content)
            
            # Convert to PlannedMeal objects
            suggested_meals = []
            for meal_data in daily_meals_data["meals"]:
                meal_type = MealType(meal_data["meal_type"])
                meal = PlannedMeal(
                    meal_type=meal_type,
                    name=meal_data["name"],
                    description=meal_data["description"],
                    prep_time=meal_data.get("prep_time", 10),
                    cook_time=meal_data.get("cook_time", 15),
                    calories=meal_data["calories"],
                    protein=meal_data["protein"],
                    carbs=meal_data["carbs"],
                    fat=meal_data["fat"],
                    ingredients=meal_data["ingredients"],
                    instructions=meal_data.get("instructions", ["Prepare and cook as desired"]),
                    is_vegetarian=meal_data.get("is_vegetarian", False),
                    is_vegan=meal_data.get("is_vegan", False),
                    is_gluten_free=meal_data.get("is_gluten_free", False),
                    cuisine_type=meal_data.get("cuisine_type", "International")
                )
                suggested_meals.append(meal)
            
            return suggested_meals
            
        except Exception as e:
            logger.error(f"Error generating unified meals: {str(e)}")
            # Fallback to individual meal generation
            logger.info("Falling back to individual meal generation")
            return self._generate_meals_individual(meal_distribution, user_preferences)
    
    def _generate_meals_individual(self, meal_distribution: Dict[MealType, float], user_preferences: Dict) -> List[PlannedMeal]:
        """Fallback method: Generate meals individually (original method)"""
        suggested_meals = []
        
        for meal_type, calorie_target in meal_distribution.items():
            try:
                meal = self._generate_meal_for_type(
                    meal_type=meal_type,
                    calorie_target=calorie_target,
                    user_preferences=user_preferences
                )
                suggested_meals.append(meal)
            except Exception as e:
                logger.error(f"Error generating {meal_type.value} meal: {str(e)}")
                # Add a fallback meal
                suggested_meals.append(self._get_fallback_meal(meal_type, calorie_target))
        
        return suggested_meals
    
    def _calculate_meal_distribution(self, total_calories: float) -> Dict[MealType, float]:
        """Calculate calorie distribution across meals"""
        from src.domain.constants import MealDistribution
        
        # Standard distribution
        distribution = {
            MealType.BREAKFAST: total_calories * MealDistribution.BREAKFAST_PERCENT,
            MealType.LUNCH: total_calories * MealDistribution.LUNCH_PERCENT,
            MealType.DINNER: total_calories * MealDistribution.DINNER_PERCENT,
        }
        
        # Add snack if total calories > threshold
        if total_calories > MealDistribution.MIN_CALORIES_FOR_SNACK:
            distribution[MealType.SNACK] = total_calories * MealDistribution.SNACK_PERCENT
            # Adjust other meals
            distribution[MealType.BREAKFAST] = total_calories * MealDistribution.BREAKFAST_WITH_SNACK
            distribution[MealType.LUNCH] = total_calories * MealDistribution.LUNCH_WITH_SNACK
            distribution[MealType.DINNER] = total_calories * MealDistribution.DINNER_WITH_SNACK
        
        return distribution
    
    def _generate_meal_for_type(self, meal_type: MealType, calorie_target: float, 
                                user_preferences: Dict) -> PlannedMeal:
        """Generate a single meal based on type and preferences"""
        
        prompt = self._build_meal_suggestion_prompt(meal_type, calorie_target, user_preferences)
        
        try:
            messages = [
                SystemMessage(content="You are a professional nutritionist creating personalized meal suggestions."),
                HumanMessage(content=prompt)
            ]
            
            response = self.model.invoke(messages)
            content = response.content
            
            # Extract JSON from response
            meal_data = self._extract_json(content)
            
            # Create PlannedMeal object
            return PlannedMeal(
                meal_type=meal_type,
                name=meal_data["name"],
                description=meal_data["description"],
                prep_time=meal_data.get("prep_time", 10),
                cook_time=meal_data.get("cook_time", 15),
                calories=meal_data["calories"],
                protein=meal_data["protein"],
                carbs=meal_data["carbs"],
                fat=meal_data["fat"],
                ingredients=meal_data["ingredients"],
                instructions=meal_data.get("instructions", ["Prepare and cook as desired"]),
                is_vegetarian=meal_data.get("is_vegetarian", False),
                is_vegan=meal_data.get("is_vegan", False),
                is_gluten_free=meal_data.get("is_gluten_free", False),
                cuisine_type=meal_data.get("cuisine_type", "International")
            )
            
        except Exception as e:
            logger.error(f"Error generating meal: {str(e)}")
            raise
    
    def _build_meal_suggestion_prompt(self, meal_type: MealType, calorie_target: float, 
                                     user_preferences: Dict) -> str:
        """Build prompt for meal generation"""
        
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
    
    def _extract_json(self, content: str) -> Dict:
        """Extract JSON from AI response"""
        try:
            # Try direct parsing
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON in markdown code block
            json_match = re.search(r'```json(.*?)```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1).strip())
            
            # Try to find any JSON-like structure
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            raise ValueError("Could not extract JSON from response")
    
    def _extract_unified_meals_json(self, content: str) -> Dict:
        """Extract JSON from unified meal response"""
        try:
            # Try direct parsing
            data = json.loads(content)
            
            # Validate structure
            if "meals" not in data or not isinstance(data["meals"], list):
                raise ValueError("Response missing 'meals' array")
            
            return data
            
        except json.JSONDecodeError:
            # Try to find JSON in markdown code block
            json_match = re.search(r'```json(.*?)```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1).strip())
                if "meals" not in data or not isinstance(data["meals"], list):
                    raise ValueError("Response missing 'meals' array")
                return data
            
            # Try to find any JSON-like structure
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if "meals" not in data or not isinstance(data["meals"], list):
                    raise ValueError("Response missing 'meals' array")
                return data
            
            raise ValueError("Could not extract unified meals JSON from response")
    
    def _build_unified_meal_prompt(self, meal_distribution: Dict[MealType, float], user_preferences: Dict) -> str:
        """Build a unified prompt for generating all daily meals at once"""
        
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
    
    def _get_fallback_meal(self, meal_type: MealType, calorie_target: float) -> PlannedMeal:
        """Return a simple fallback meal if generation fails"""
        
        # Scale portions based on calorie target
        scale_factor = calorie_target / 400  # Base meals are ~400 calories
        
        fallback_meals = {
            MealType.BREAKFAST: {
                "name": "Protein Oatmeal Bowl",
                "description": "Hearty oatmeal with protein powder and fruits",
                "prep_time": 5,
                "cook_time": 5,
                "calories": int(400 * scale_factor),
                "protein": int(25 * scale_factor),
                "carbs": int(55 * scale_factor),
                "fat": int(10 * scale_factor),
                "ingredients": [
                    f"{int(60 * scale_factor)}g rolled oats",
                    f"{int(30 * scale_factor)}g protein powder",
                    "1 medium banana",
                    "1 tablespoon almond butter",
                    "Cinnamon to taste"
                ],
                "instructions": [
                    "Cook oats with water or milk",
                    "Stir in protein powder",
                    "Top with sliced banana and almond butter",
                    "Sprinkle with cinnamon"
                ],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": False
            },
            MealType.LUNCH: {
                "name": "Grilled Chicken Salad Bowl",
                "description": "Fresh salad with grilled chicken and vegetables",
                "prep_time": 15,
                "cook_time": 15,
                "calories": int(450 * scale_factor),
                "protein": int(35 * scale_factor),
                "carbs": int(30 * scale_factor),
                "fat": int(20 * scale_factor),
                "ingredients": [
                    f"{int(150 * scale_factor)}g grilled chicken breast",
                    "Mixed greens",
                    "Cherry tomatoes",
                    "Cucumber",
                    "Avocado",
                    "Olive oil vinaigrette"
                ],
                "instructions": [
                    "Grill chicken breast",
                    "Prepare salad greens and vegetables",
                    "Slice grilled chicken",
                    "Assemble bowl and dress"
                ],
                "is_vegetarian": False,
                "is_vegan": False,
                "is_gluten_free": True
            },
            MealType.DINNER: {
                "name": "Baked Salmon with Vegetables",
                "description": "Omega-3 rich salmon with roasted vegetables",
                "prep_time": 10,
                "cook_time": 25,
                "calories": int(500 * scale_factor),
                "protein": int(40 * scale_factor),
                "carbs": int(35 * scale_factor),
                "fat": int(22 * scale_factor),
                "ingredients": [
                    f"{int(180 * scale_factor)}g salmon fillet",
                    "Broccoli",
                    "Sweet potato",
                    "Olive oil",
                    "Lemon",
                    "Herbs"
                ],
                "instructions": [
                    "Season salmon with herbs",
                    "Prepare vegetables",
                    "Bake everything at 400°F for 20-25 minutes",
                    "Serve with lemon"
                ],
                "is_vegetarian": False,
                "is_vegan": False,
                "is_gluten_free": True
            },
            MealType.SNACK: {
                "name": "Greek Yogurt with Berries",
                "description": "High-protein snack with antioxidants",
                "prep_time": 2,
                "cook_time": 0,
                "calories": int(200 * scale_factor),
                "protein": int(15 * scale_factor),
                "carbs": int(20 * scale_factor),
                "fat": int(5 * scale_factor),
                "ingredients": [
                    f"{int(170 * scale_factor)}g Greek yogurt",
                    "Mixed berries",
                    "Honey (optional)"
                ],
                "instructions": [
                    "Add berries to yogurt",
                    "Drizzle with honey if desired"
                ],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": True
            }
        }
        
        meal_data = fallback_meals.get(meal_type, fallback_meals[MealType.LUNCH])
        return PlannedMeal(meal_type=meal_type, **meal_data)