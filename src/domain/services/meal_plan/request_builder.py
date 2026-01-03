"""Request and context building logic."""
from typing import Dict, Any, Optional

from src.domain.model.meal_planning import (
    MealGenerationRequest, MealGenerationType,
    UserDietaryProfile, UserNutritionTargets,
    IngredientConstraints, MealGenerationContext
)
from src.domain.services.meal_distribution_service import MealDistributionService
from src.domain.services.meal_type_determination_service import MealTypeDeterminationService


class RequestBuilder:
    """Builds generation requests and contexts from raw data."""

    def __init__(
        self,
        meal_distribution_service: MealDistributionService,
        meal_type_service: MealTypeDeterminationService
    ):
        self.meal_distribution_service = meal_distribution_service
        self.meal_type_service = meal_type_service

    def build_generation_request(
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

    def create_generation_context(
        self, generation_request: MealGenerationRequest, request_data: Optional[Dict[str, Any]] = None
    ) -> MealGenerationContext:
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

    @staticmethod
    def convert_request_to_dict(
        generation_request: MealGenerationRequest, request_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert generation_request back to request_data format for compatibility."""
        return {
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
            "include_snacks": generation_request.user_profile.include_snacks,
            "start_date_obj": request_data.get("start_date_obj") if request_data else None,
            "end_date_obj": request_data.get("end_date_obj") if request_data else None
        }
