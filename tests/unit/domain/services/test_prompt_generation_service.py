"""
Unit tests for PromptGenerationService.
"""
import pytest

from src.domain.services.prompt_generation_service import PromptGenerationService
from src.domain.model import (
    MealGenerationContext, MealGenerationRequest, MealGenerationType,
    UserDietaryProfile, UserNutritionTargets, IngredientConstraints, MealType
)


@pytest.fixture
def service():
    """Create PromptGenerationService instance."""
    return PromptGenerationService()


@pytest.fixture
def user_profile():
    """Create sample user profile."""
    return UserDietaryProfile(
        user_id="123",
        meals_per_day=3,
        dietary_preferences=["vegetarian"],
        allergies=[],
        health_conditions=[],
        activity_level="moderately_active",
        fitness_goal="recomp",
        include_snacks=True
    )


@pytest.fixture
def nutrition_targets():
    """Create sample nutrition targets."""
    return UserNutritionTargets(
        calories=2000,
        protein=150.0,
        carbs=250.0,
        fat=67.0
    )


class TestPromptGenerationService:
    """Test suite for PromptGenerationService."""

    def test_generate_weekly_ingredient_prompt(self, service, user_profile, nutrition_targets):
        """Test generating weekly ingredient-based prompt."""
        ingredients = IngredientConstraints(
            available_ingredients=["chicken breast", "brown rice", "broccoli"],
            available_seasonings=["salt", "pepper", "olive oil"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.WEEKLY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        
        prompt, system_message = service.generate_prompt_and_system_message(context)
        
        assert "7-day meal plan" in prompt
        assert "chicken breast" in prompt
        assert "brown rice" in prompt
        assert "salt" in prompt
        assert "2000" in prompt  # calories
        assert "150" in prompt or "150.0" in prompt  # protein
        assert "vegetarian" in prompt.lower() or "dietary" in prompt.lower()
        assert system_message is not None

    def test_generate_daily_ingredient_prompt(self, service, user_profile, nutrition_targets):
        """Test generating daily ingredient-based prompt."""
        ingredients = IngredientConstraints(
            available_ingredients=["salmon", "quinoa", "asparagus"],
            available_seasonings=["lemon", "garlic", "thyme"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        
        prompt, system_message = service.generate_prompt_and_system_message(context)
        
        assert "daily meal plan" in prompt.lower() or "meals" in prompt.lower()
        assert "salmon" in prompt
        assert "quinoa" in prompt
        assert "lemon" in prompt
        assert "2000" in prompt
        assert system_message is not None

    def test_generate_daily_profile_prompt(self, service, user_profile, nutrition_targets):
        """Test generating daily profile-based prompt."""
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_PROFILE_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        
        prompt, system_message = service.generate_prompt_and_system_message(context)
        
        assert "daily meal plan" in prompt.lower() or "meal" in prompt.lower()
        assert "recomp" in prompt.lower()
        assert "moderately_active" in prompt.lower() or "activity" in prompt.lower()
        assert "vegetarian" in prompt.lower()
        assert system_message is not None

    def test_generate_prompt_unsupported_type(self, service, user_profile, nutrition_targets):
        """Test error for unsupported generation type."""
        request = MealGenerationRequest(
            generation_type="UNSUPPORTED_TYPE",
            user_profile=user_profile,
            nutrition_targets=nutrition_targets
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        
        with pytest.raises(ValueError, match="Unsupported generation type"):
            service.generate_prompt_and_system_message(context)

    def test_generate_single_ingredient_meal_prompt(self, service, user_profile, nutrition_targets):
        """Test generating single ingredient-based meal prompt."""
        ingredients = IngredientConstraints(
            available_ingredients=["chicken", "rice", "vegetables"],
            available_seasonings=["salt", "pepper"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        
        prompt, system_message = service.generate_single_meal_prompt(
            meal_type=MealType.BREAKFAST,
            calorie_target=500,
            context=context
        )
        
        assert "breakfast" in prompt.lower()
        assert "500" in prompt
        assert "chicken" in prompt
        assert "salt" in prompt
        assert system_message is not None

    def test_generate_single_profile_meal_prompt(self, service, user_profile, nutrition_targets):
        """Test generating single profile-based meal prompt."""
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_PROFILE_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        
        prompt, system_message = service.generate_single_meal_prompt(
            meal_type=MealType.DINNER,
            calorie_target=700,
            context=context
        )
        
        assert "dinner" in prompt.lower()
        assert "700" in prompt
        assert "recomp" in prompt.lower()
        assert system_message is not None

    def test_prompt_includes_dietary_preferences(self, service, nutrition_targets):
        """Test that dietary preferences are included in prompt."""
        user_profile = UserDietaryProfile(
            user_id="123",
            meals_per_day=3,
            include_snacks=True,
            dietary_preferences=["vegan", "gluten_free"],
            health_conditions=[],
            allergies=[],
            fitness_goal="cut",
            activity_level="very_active"
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_PROFILE_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        prompt, _ = service.generate_prompt_and_system_message(context)
        
        assert "vegan" in prompt.lower()
        assert "gluten" in prompt.lower()

    def test_prompt_includes_allergies(self, service, nutrition_targets):
        """Test that allergies are included in prompt."""
        user_profile = UserDietaryProfile(
            user_id="123",
            meals_per_day=3,
            include_snacks=True,
            dietary_preferences=[],
            health_conditions=[],
            allergies=["shellfish", "tree nuts", "dairy"],
            fitness_goal="bulk",
            activity_level="extra_active"
        )
        
        ingredients = IngredientConstraints(
            available_ingredients=["beef", "rice"],
            available_seasonings=["salt"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        prompt, _ = service.generate_single_meal_prompt(
            meal_type=MealType.LUNCH,
            calorie_target=600,
            context=context
        )
        
        # Allergies should be mentioned
        prompt_lower = prompt.lower()
        assert "allerg" in prompt_lower or "avoid" in prompt_lower

    def test_prompt_includes_calorie_distribution(self, service, user_profile, nutrition_targets):
        """Test that prompt includes calorie distribution for meals."""
        ingredients = IngredientConstraints(
            available_ingredients=["chicken"],
            available_seasonings=["salt"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.WEEKLY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        # Provide calorie distribution for meals
        from src.domain.model import CalorieDistribution
        calorie_dist = CalorieDistribution(
            distribution={
                MealType.BREAKFAST: 600,
                MealType.LUNCH: 700,
                MealType.DINNER: 700
            }
        )
        
        context = MealGenerationContext(
            request=request, 
            calorie_distribution=calorie_dist, 
            meal_types=[MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER], 
            start_date=None, 
            end_date=None
        )
        prompt, _ = service.generate_prompt_and_system_message(context)
        
        # Should include meal-specific calorie targets
        assert "breakfast" in prompt.lower() or "Breakfast" in prompt
        assert "lunch" in prompt.lower() or "Lunch" in prompt
        assert "dinner" in prompt.lower() or "Dinner" in prompt

    def test_prompt_requires_exact_portions(self, service, user_profile, nutrition_targets):
        """Test that prompts require exact ingredient portions."""
        ingredients = IngredientConstraints(
            available_ingredients=["chicken breast", "rice"],
            available_seasonings=["salt", "pepper"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        prompt, _ = service.generate_prompt_and_system_message(context)
        
        # Should emphasize exact measurements
        prompt_lower = prompt.lower()
        assert "exact" in prompt_lower or "precise" in prompt_lower or "measurement" in prompt_lower
        assert "gram" in prompt_lower or "ml" in prompt_lower or "portion" in prompt_lower

    def test_prompt_includes_cooking_times(self, service, user_profile, nutrition_targets):
        """Test that prompts mention cooking times."""
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_PROFILE_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        prompt, _ = service.generate_prompt_and_system_message(context)
        
        # Should mention time considerations
        prompt_lower = prompt.lower()
        assert "time" in prompt_lower or "quick" in prompt_lower or "prep" in prompt_lower

    def test_prompt_with_health_conditions(self, service, nutrition_targets):
        """Test prompt generation with health conditions."""
        user_profile = UserDietaryProfile(
            user_id="123",
            meals_per_day=3,
            include_snacks=True,
            dietary_preferences=[],
            health_conditions=["diabetes", "hypertension"],
            allergies=[],
            fitness_goal="recomp",
            activity_level="lightly_active"
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_PROFILE_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        prompt, _ = service.generate_prompt_and_system_message(context)
        
        # Health conditions should be mentioned
        assert "diabetes" in prompt.lower()
        assert "hypertension" in prompt.lower()

    def test_prompt_with_snacks(self, service, nutrition_targets):
        """Test prompt includes snacks when requested."""
        user_profile = UserDietaryProfile(
            user_id="123",
            meals_per_day=3,
            include_snacks=True,
            dietary_preferences=[],
            health_conditions=[],
            allergies=[],
            fitness_goal="recomp",
            activity_level="moderately_active",
        )
        
        ingredients = IngredientConstraints(
            available_ingredients=["chicken"],
            available_seasonings=["salt"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.WEEKLY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        prompt, _ = service.generate_prompt_and_system_message(context)
        
        assert "snack" in prompt.lower()

    def test_prompt_without_snacks(self, service, nutrition_targets):
        """Test prompt excludes snacks when not requested."""
        user_profile = UserDietaryProfile(
            user_id="123",
            meals_per_day=3,
            include_snacks=False,
            dietary_preferences=[],
            health_conditions=[],
            allergies=[],
            fitness_goal="recomp",
            activity_level="moderately_active",
        )
        
        ingredients = IngredientConstraints(
            available_ingredients=["chicken"],
            available_seasonings=["salt"]
        )
        
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_INGREDIENT_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets,
            ingredient_constraints=ingredients
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        prompt, _ = service.generate_prompt_and_system_message(context)
        
        # Snack requirement should not be present
        assert "snack" not in prompt.lower() or "no snack" in prompt.lower()

    def test_system_message_is_consistent(self, service, user_profile, nutrition_targets):
        """Test that system messages are appropriate for meal planning."""
        request = MealGenerationRequest(
            generation_type=MealGenerationType.DAILY_PROFILE_BASED,
            user_profile=user_profile,
            nutrition_targets=nutrition_targets
        )
        
        context = MealGenerationContext(request=request, calorie_distribution=None, meal_types=[], start_date=None, end_date=None)
        _, system_message = service.generate_prompt_and_system_message(context)
        
        # System message should establish expertise
        system_lower = system_message.lower()
        assert "nutrition" in system_lower or "meal" in system_lower or "chef" in system_lower

