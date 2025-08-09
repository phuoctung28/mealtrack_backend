"""
Meal plan orchestration service.
Uses the unified LLM adapter with different prompts for different meal plan types.
"""
import logging
from typing import Dict, Any, List
from datetime import date, datetime, timedelta

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.model.meal_generation_request import (
    MealGenerationRequest, MealGenerationType, UserDietaryProfile, 
    UserNutritionTargets, IngredientConstraints, MealGenerationContext
)
from src.domain.model.meal_generation_response import (
    DailyMealPlan, WeeklyMealPlan, GeneratedMeal, NutritionSummary
)
from src.domain.model.meal_plan import MealType
from src.domain.services.meal_distribution_service import MealDistributionService
from src.domain.services.meal_type_determination_service import MealTypeDeterminationService
from src.domain.services.fallback_meal_service import FallbackMealService
from src.domain.services.prompt_generation_service import PromptGenerationService

logger = logging.getLogger(__name__)


class MealPlanOrchestrationService:
    """
    Orchestrates meal plan generation using unified LLM service with different prompts.
    Handles all business logic while delegating LLM calls to the adapter.
    """
    
    def __init__(self, meal_generation_service: MealGenerationServicePort):
        self.meal_generation_service = meal_generation_service
        self.meal_distribution_service = MealDistributionService()
        self.meal_type_service = MealTypeDeterminationService()
        self.fallback_service = FallbackMealService()
        self.prompt_service = PromptGenerationService()
    
    def generate_weekly_ingredient_based_plan(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate weekly meal plan based on ingredients."""
        # Convert request data to domain model
        generation_request = self._build_generation_request(
            request_data, MealGenerationType.WEEKLY_INGREDIENT_BASED
        )
        
        # Create generation context
        context = self._create_generation_context(generation_request, request_data)
        
        try:
            # Generate prompt using domain service
            prompt, system_message = self.prompt_service.generate_prompt_and_system_message(context)
            
            # Generate using unified LLM service
            raw_data = self.meal_generation_service.generate_meal_plan(prompt, system_message, "json")
            
            # Validate and process response
            self._validate_weekly_response(raw_data, request_data)
            
            # Transform to expected format
            flat_meals = self._flatten_week(raw_data["week"])
            
            # Validate and adjust nutritional targets
            validated_meals = self._validate_and_adjust_weekly_nutrition(flat_meals, generation_request)
            
            return self._format_weekly_response(validated_meals, request_data)
            
        except Exception as e:
            logger.error(f"Error generating weekly meal plan: {str(e)}")
            logger.info("Falling back to individual daily meal generation")
            
            # Fallback: Generate day by day using daily method
            fallback_meals = self._generate_weekly_fallback(context, generation_request, request_data)
            return fallback_meals
    
    def generate_daily_ingredient_based_plan(self, request_data: Dict[str, Any]) -> DailyMealPlan:
        """Generate daily meal plan based on ingredients."""
        # Convert request data to domain model
        generation_request = self._build_generation_request(
            request_data, MealGenerationType.DAILY_INGREDIENT_BASED
        )
        
        # Create generation context
        context = self._create_generation_context(generation_request)
        
        # Generate meals using domain services
        generated_meals = []
        total_nutrition = NutritionSummary(calories=0, protein=0.0, carbs=0.0, fat=0.0)
        
        for meal_type in context.meal_types:
            calorie_target = context.calorie_distribution.get_calories_for_meal(meal_type)
            
            try:
                # Generate prompt for this specific meal
                prompt, system_message = self.prompt_service.generate_single_meal_prompt(
                    meal_type, calorie_target, context
                )
                
                # Generate using unified LLM service
                meal_data = self.meal_generation_service.generate_meal_plan(prompt, system_message, "json")
                
                # Convert to domain model
                generated_meal = self._convert_to_generated_meal(meal_data, meal_type)
                generated_meals.append(generated_meal)
                
                # Add to totals
                total_nutrition.calories += generated_meal.nutrition.calories
                total_nutrition.protein += generated_meal.nutrition.protein
                total_nutrition.carbs += generated_meal.nutrition.carbs
                total_nutrition.fat += generated_meal.nutrition.fat
                
            except Exception as e:
                logger.error(f"Error generating {meal_type.value} meal: {str(e)}")
                # Use fallback meal from domain service
                fallback_meal = self.fallback_service.get_fallback_meal(meal_type, calorie_target)
                generated_meals.append(fallback_meal)
                
                total_nutrition.calories += fallback_meal.nutrition.calories
                total_nutrition.protein += fallback_meal.nutrition.protein
                total_nutrition.carbs += fallback_meal.nutrition.carbs
                total_nutrition.fat += fallback_meal.nutrition.fat
        
        # Create daily meal plan domain model
        daily_plan = DailyMealPlan(
            user_id=generation_request.user_profile.user_id,
            plan_date=date.today(),
            meals=generated_meals
        )
        
        # Return the domain model directly
        return daily_plan
    
    def generate_daily_plan(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate daily meal plan based on user preferences (non-ingredient based)."""
        # Convert request data to domain model
        generation_request = self._build_generation_request(
            user_preferences, MealGenerationType.DAILY_PROFILE_BASED
        )
        
        # Create generation context
        context = self._create_generation_context(generation_request)
        
        # Generate prompt using domain service
        prompt, system_message = self.prompt_service.generate_prompt_and_system_message(context)

        try:
            # Generate all meals using unified LLM service
            response_data = self.meal_generation_service.generate_meal_plan(prompt, system_message, "json")
            
            # Validate structure
            if "meals" not in response_data or not isinstance(response_data["meals"], list):
                raise ValueError("Response missing 'meals' array")
            
            # Convert to domain models
            generated_meals = []
            total_nutrition = NutritionSummary(calories=0, protein=0.0, carbs=0.0, fat=0.0)
            
            for meal_data in response_data["meals"]:
                meal_type = MealType(meal_data.get("meal_type", "breakfast"))
                generated_meal = self._convert_to_generated_meal(meal_data, meal_type)
                generated_meals.append(generated_meal)
                
                # Add to totals
                total_nutrition.calories += generated_meal.nutrition.calories
                total_nutrition.protein += generated_meal.nutrition.protein
                total_nutrition.carbs += generated_meal.nutrition.carbs
                total_nutrition.fat += generated_meal.nutrition.fat
            
            # Create daily meal plan domain model
            daily_plan = DailyMealPlan(
                user_id=generation_request.user_profile.user_id,
                plan_date=date.today(),
                meals=generated_meals
            )
            
            # Convert to API response format
            return self._convert_daily_plan_to_response(daily_plan, generation_request)
            
        except Exception as e:
            logger.error(f"Error generating unified daily meal plan: {str(e)}")
            # Fallback to individual meal generation
            logger.info("Falling back to individual meal generation")
            fallback_request_data = {
                **user_preferences,
                "available_ingredients": ["chicken", "rice", "vegetables", "eggs", "milk", "bread", "fruits"],
                "available_seasonings": ["salt", "pepper", "herbs", "spices"]
            }
            return self.generate_daily_ingredient_based_plan(fallback_request_data)
    
    def _build_generation_request(
        self, request_data: Dict[str, Any], generation_type: MealGenerationType
    ) -> MealGenerationRequest:
        """Build domain model from request data."""
        # Build user profile
        user_profile = UserDietaryProfile(
            user_id=request_data.get("user_id", "unknown"),
            dietary_preferences=request_data.get("dietary_preferences", []),
            health_conditions=request_data.get("health_conditions", []),
            allergies=request_data.get("allergies", []),
            activity_level=request_data.get("activity_level", "moderate"),
            fitness_goal=request_data.get("fitness_goal", "maintenance"),
            meals_per_day=request_data.get("meals_per_day", 3),
            include_snacks=request_data.get("include_snacks", False)
        )
        
        # Build nutrition targets
        nutrition_targets = UserNutritionTargets(
            calories=request_data.get("target_calories", 1800),
            protein=request_data.get("target_protein", 120.0),
            carbs=request_data.get("target_carbs", 200.0),
            fat=request_data.get("target_fat", 80.0)
        )
        
        # Build ingredient constraints if applicable
        ingredient_constraints = None
        if "available_ingredients" in request_data or "available_seasonings" in request_data:
            ingredient_constraints = IngredientConstraints(
                available_ingredients=request_data.get("available_ingredients", []),
                available_seasonings=request_data.get("available_seasonings", [])
            )
        
        return MealGenerationRequest(
            generation_type=generation_type,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredient_constraints
        )
    
    def _create_generation_context(self, generation_request: MealGenerationRequest, request_data: Dict[str, Any] = None) -> MealGenerationContext:
        """Create generation context from request."""
        # Determine meal types using domain service
        meal_types = self.meal_type_service.determine_meal_types(
            generation_request.user_profile.meals_per_day,
            generation_request.user_profile.include_snacks
        )
        
        # Calculate calorie distribution using domain service
        calorie_distribution = self.meal_distribution_service.calculate_distribution(
            meal_types, generation_request.nutrition_targets
        )
        
        # Extract dates if provided
        start_date = None
        end_date = None
        if request_data:
            start_date = request_data.get("start_date_obj")
            end_date = request_data.get("end_date_obj")
        
        return MealGenerationContext(
            request=generation_request,
            meal_types=meal_types,
            calorie_distribution=calorie_distribution,
            start_date=start_date,
            end_date=end_date
        )
    
    def _convert_to_generated_meal(self, meal_data: Dict[str, Any], meal_type: MealType) -> GeneratedMeal:
        """Convert LLM response to domain model."""
        nutrition = NutritionSummary(
            calories=int(meal_data.get("calories", 0)),
            protein=float(meal_data.get("protein", 0.0)),
            carbs=float(meal_data.get("carbs", 0.0)),
            fat=float(meal_data.get("fat", 0.0))
        )
        
        return GeneratedMeal(
            meal_id=f"meal_{meal_type.value}_{hash(str(meal_data)) % 10000}",
            meal_type=meal_type.value,
            name=meal_data.get("name", f"Simple {meal_type.value.title()}"),
            description=meal_data.get("description", f"A nutritious {meal_type.value}"),
            prep_time=meal_data.get("prep_time", 15),
            cook_time=meal_data.get("cook_time", 20),
            nutrition=nutrition,
            ingredients=meal_data.get("ingredients", ["Basic ingredients"]),
            instructions=meal_data.get("instructions", ["Prepare and cook as desired"]),
            is_vegetarian=meal_data.get("is_vegetarian", False),
            is_vegan=meal_data.get("is_vegan", False),
            is_gluten_free=meal_data.get("is_gluten_free", False),
            cuisine_type=meal_data.get("cuisine_type", "International")
        )
    
    def _convert_daily_plan_to_response(self, daily_plan: DailyMealPlan, request: MealGenerationRequest) -> DailyMealPlan:
        """Convert domain model to API response format (now returns the domain model directly)."""
        # Return the domain model directly - conversion to API response will happen at the API layer
        return daily_plan
    
    def _validate_weekly_response(self, data: Dict[str, Any], request: Dict[str, Any]) -> None:
        """Validate weekly response structure."""
        week_data = data.get("week", [])
        if len(week_data) != 7:
            raise ValueError(f"Expected 7 days, got {len(week_data)}")
        
        required_fields = {"meal_type", "name", "calories", "protein", "carbs", "fat", 
                          "ingredients", "instructions", "is_vegetarian", "is_vegan", 
                          "is_gluten_free", "cuisine_type"}
        
        include_snacks = request.get("include_snacks", False)
        expected_meals_per_day = 3 + (1 if include_snacks else 0)
        
        for day in week_data:
            day_name = day.get("day", "")
            meals = day.get("meals", [])
            
            if len(meals) < expected_meals_per_day:
                logger.warning(f"{day_name}: Expected {expected_meals_per_day} meals, got {len(meals)}")
            
            for meal in meals:
                missing_fields = required_fields - meal.keys()
                if missing_fields:
                    logger.warning(f"{day_name} meal missing fields: {missing_fields}")
    
    def _flatten_week(self, week_block):
        """Flatten week structure to meal list."""
        meals = []
        for day in week_block:
            for meal in day["meals"]:
                meals.append({"day": day["day"], **meal})
        return meals
    
    def _format_weekly_response(self, meals, request_data):
        """Format weekly response structure."""
        # Use provided start/end dates if available, otherwise calculate current week
        if "start_date_obj" in request_data and "end_date_obj" in request_data:
            start_date = request_data["start_date_obj"]
            end_date = request_data["end_date_obj"]
        else:
            # Fallback to current week calculation
            today = datetime.now().date()
            days_since_monday = today.weekday()  # Monday = 0
            start_date = today - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=6)
        
        # Create day name to date mapping
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_to_date = {}
        for i, day_name in enumerate(day_names):
            day_date = start_date + timedelta(days=i)
            day_to_date[day_name] = day_date
        
        # Ensure all meals have required dietary fields and add dates
        for meal in meals:
            meal.setdefault("is_vegetarian", False)
            meal.setdefault("is_vegan", False)
            meal.setdefault("is_gluten_free", False)
            meal.setdefault("cuisine_type", "International")
            
            # Add actual date and formatted day string
            if meal["day"] in day_to_date:
                meal_date = day_to_date[meal["day"]]
                meal["date"] = meal_date.isoformat()
                meal["day_formatted"] = f"{meal['day']}, {meal_date.strftime('%B %d, %Y')}"
            else:
                # Fallback for unknown day names
                meal["date"] = start_date.isoformat()
                meal["day_formatted"] = meal["day"]
        
        total_cals = sum(m["calories"] for m in meals)
        total_prot = sum(m["protein"] for m in meals)
        total_carbs = sum(m["carbs"] for m in meals)
        total_fat = sum(m["fat"] for m in meals)

        # Group by day name - schema expects each day to map directly to a list of meals
        grouped = {}
        for m in meals:
            day_name = m["day"]
            if day_name not in grouped:
                grouped[day_name] = []
            grouped[day_name].append(m)

        return {
            "user_id": request_data.get("user_id", "unknown"),
            "plan_type": "weekly",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": grouped,
            "meals": meals,
            "total_nutrition": {
                "calories": total_cals,
                "protein": round(total_prot, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1),
            },
            "daily_average_nutrition": {
                "calories": total_cals // 7,
                "protein": round(total_prot / 7, 1),
                "carbs": round(total_carbs / 7, 1),
                "fat": round(total_fat / 7, 1),
            },
            "target_nutrition": {
                "calories": request_data.get("target_calories", 1800),
                "protein": request_data.get("target_protein", 120.0),
                "carbs": request_data.get("target_carbs", 200.0),
                "fat": request_data.get("target_fat", 80.0),
            },
            "user_preferences": {
                "dietary_preferences": request_data.get("dietary_preferences", []),
                "health_conditions": request_data.get("health_conditions", []),
                "allergies": request_data.get("allergies", []),
                "activity_level": request_data.get("activity_level", "moderate"),
                "fitness_goal": request_data.get("fitness_goal", "maintenance"),
                "meals_per_day": request_data.get("meals_per_day", 3),
                "snacks_per_day": 1 if request_data.get("include_snacks", False) else 0,
            },
        }
    
    def _generate_weekly_fallback(self, context: MealGenerationContext, generation_request: MealGenerationRequest, request_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate weekly plan using fallback meals when LLM generation fails."""
        from datetime import datetime, timedelta
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        all_meals = []
        
        # Use provided start date if available, otherwise calculate current week
        if request_data and "start_date_obj" in request_data:
            start_date = request_data["start_date_obj"]
        else:
            # Fallback to current week calculation
            today = datetime.now().date()
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
        
        # Generate meals for each day using fallback service
        for i, day_name in enumerate(days):
            daily_meals = []
            for meal_type in context.meal_types:
                calorie_target = context.calorie_distribution.get_calories_for_meal(meal_type)
                fallback_meal = self.fallback_service.get_fallback_meal(meal_type, calorie_target)
                
                # Calculate date for this day
                day_date = start_date + timedelta(days=i)
                
                # Convert to dict format expected by weekly response
                meal_dict = {
                    "day": day_name,
                    "date": day_date.isoformat(),
                    "day_formatted": f"{day_name}, {day_date.strftime('%B %d, %Y')}",
                    "meal_type": fallback_meal.meal_type,
                    "name": fallback_meal.name,
                    "description": fallback_meal.description,
                    "calories": fallback_meal.nutrition.calories,
                    "protein": fallback_meal.nutrition.protein,
                    "carbs": fallback_meal.nutrition.carbs,
                    "fat": fallback_meal.nutrition.fat,
                    "prep_time": fallback_meal.prep_time,
                    "cook_time": fallback_meal.cook_time,
                    "ingredients": fallback_meal.ingredients,
                    "instructions": fallback_meal.instructions,
                    "is_vegetarian": fallback_meal.is_vegetarian,
                    "is_vegan": fallback_meal.is_vegan,
                    "is_gluten_free": fallback_meal.is_gluten_free,
                    "cuisine_type": fallback_meal.cuisine_type
                }
                daily_meals.append(meal_dict)
                all_meals.append(meal_dict)
        
        # Convert generation_request back to request_data format for compatibility
        request_data = {
            "user_id": generation_request.user_profile.user_id,
            "target_calories": generation_request.nutrition_targets.calories,
            "target_protein": generation_request.nutrition_targets.protein,
            "target_carbs": generation_request.nutrition_targets.carbs,
            "target_fat": generation_request.nutrition_targets.fat,
            "dietary_preferences": generation_request.user_profile.dietary_preferences,
            "health_conditions": generation_request.user_profile.health_conditions,
            "allergies": generation_request.user_profile.allergies,
            "activity_level": generation_request.user_profile.activity_level,
            "fitness_goal": generation_request.user_profile.fitness_goal,
            "meals_per_day": generation_request.user_profile.meals_per_day,
            "include_snacks": generation_request.user_profile.include_snacks
        }
        
        # Validate and adjust nutritional targets for fallback meals too
        validated_meals = self._validate_and_adjust_weekly_nutrition(all_meals, generation_request)
        
        return self._format_weekly_response(validated_meals, request_data)
    
    def _calculate_nutrition_totals(self, meals: List[Dict]) -> Dict[str, float]:
        """Helper method to calculate nutrition totals from meals."""
        return {
            "calories": sum(meal["calories"] for meal in meals),
            "protein": sum(meal["protein"] for meal in meals),
            "carbs": sum(meal["carbs"] for meal in meals),
            "fat": sum(meal["fat"] for meal in meals)
        }
    
    def _validate_and_adjust_weekly_nutrition(self, meals: List[Dict], generation_request: MealGenerationRequest) -> List[Dict]:
        """Validate and adjust weekly nutrition to match targets."""
        target_nutrition = generation_request.nutrition_targets
        expected_weekly_totals = {
            "calories": target_nutrition.calories * 7,
            "protein": target_nutrition.protein * 7,
            "carbs": target_nutrition.carbs * 7,
            "fat": target_nutrition.fat * 7
        }
        
        # Calculate current totals using helper method
        current_totals = self._calculate_nutrition_totals(meals)
        
        # Check if adjustment is needed (allow 5% tolerance)
        tolerance = 0.05
        needs_adjustment = any(
            abs(current_totals[nutrient] - expected_weekly_totals[nutrient]) > expected_weekly_totals[nutrient] * tolerance
            for nutrient in expected_weekly_totals
        )
        
        if not needs_adjustment:
            logger.info("Weekly nutrition targets are within acceptable range")
            return meals
        
        logger.warning(f"Weekly nutrition adjustment needed. Current: {current_totals}")
        logger.warning(f"Expected: {expected_weekly_totals}")
        
        # Calculate adjustment factors
        adjustment_factors = {
            nutrient: expected_weekly_totals[nutrient] / current_totals[nutrient] if current_totals[nutrient] > 0 else 1
            for nutrient in expected_weekly_totals
        }
        
        # Apply adjustments proportionally
        adjusted_meals = []
        for meal in meals:
            adjusted_meal = meal.copy()
            adjusted_meal["calories"] = int(meal["calories"] * adjustment_factors["calories"])
            adjusted_meal["protein"] = round(meal["protein"] * adjustment_factors["protein"], 1)
            adjusted_meal["carbs"] = round(meal["carbs"] * adjustment_factors["carbs"], 1)
            adjusted_meal["fat"] = round(meal["fat"] * adjustment_factors["fat"], 1)
            adjusted_meals.append(adjusted_meal)
        
        # Verify final totals using helper method
        final_totals = self._calculate_nutrition_totals(adjusted_meals)
        logger.info(f"Adjusted weekly nutrition: {final_totals}")
        
        return adjusted_meals