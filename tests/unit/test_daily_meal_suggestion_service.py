"""
Unit tests for DailyMealSuggestionService.
"""
import pytest
from unittest.mock import patch
import json

from src.domain.services.daily_meal_suggestion_service import DailyMealSuggestionService
from src.domain.model.meal_plan import MealType, PlannedMeal
from src.domain.model.macro_targets import SimpleMacroTargets


@pytest.fixture
def service():
    """Create DailyMealSuggestionService instance with mocked LLM."""
    with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
        service = DailyMealSuggestionService()
        return service


@pytest.fixture
def user_preferences():
    """Create sample user preferences."""
    return {
        'age': 30,
        'gender': 'male',
        'height': 175,
        'weight': 75,
        'activity_level': 'moderately_active',
        'goal': 'maintenance',
        'dietary_preferences': ['vegetarian'],
        'health_conditions': [],
        'target_calories': 2000,
        'target_macros': SimpleMacroTargets(protein=150.0, carbs=250.0, fat=67.0)
    }


class TestDailyMealSuggestionService:
    """Test suite for DailyMealSuggestionService."""

    @patch.dict('os.environ', {}, clear=True)
    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            DailyMealSuggestionService()

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'})
    def test_init_with_api_key(self):
        """Test successful initialization."""
        service = DailyMealSuggestionService()
        assert service.google_api_key == 'test_key'
        assert service.model is not None

    def test_calculate_meal_distribution_without_snack(self, service):
        """Test meal distribution for lower calorie target (no snack)."""
        distribution = service._calculate_meal_distribution(1800)
        
        assert MealType.BREAKFAST in distribution
        assert MealType.LUNCH in distribution
        assert MealType.DINNER in distribution
        assert MealType.SNACK not in distribution
        
        # Verify distribution sums approximately to total
        total = sum(distribution.values())
        assert abs(total - 1800) < 50  # Allow small rounding error

    def test_calculate_meal_distribution_with_snack(self, service):
        """Test meal distribution for higher calorie target (with snack)."""
        distribution = service._calculate_meal_distribution(2500)
        
        assert MealType.BREAKFAST in distribution
        assert MealType.LUNCH in distribution
        assert MealType.DINNER in distribution
        assert MealType.SNACK in distribution
        
        # Snack should be included
        assert distribution[MealType.SNACK] > 0

    def test_build_meal_suggestion_prompt(self, service, user_preferences):
        """Test building meal suggestion prompt."""
        prompt = service._build_meal_suggestion_prompt(
            meal_type=MealType.BREAKFAST,
            calorie_target=500,
            user_preferences=user_preferences
        )
        
        assert "breakfast" in prompt.lower()
        assert "500" in prompt
        assert "vegetarian" in prompt.lower()
        assert "maintenance" in prompt.lower()
        assert "JSON" in prompt

    def test_extract_json_direct(self, service):
        """Test extracting JSON directly."""
        content = '{"name": "meal", "calories": 500}'
        result = service._extract_json(content)
        
        assert result == {"name": "meal", "calories": 500}

    def test_extract_json_from_markdown(self, service):
        """Test extracting JSON from markdown code block."""
        content = '''Here's your meal:
```json
{"name": "salad", "calories": 300}
```
'''
        result = service._extract_json(content)
        
        assert result == {"name": "salad", "calories": 300}

    def test_extract_json_invalid(self, service):
        """Test error when JSON cannot be extracted."""
        content = "This is not JSON"
        
        with pytest.raises(ValueError, match="Could not extract JSON"):
            service._extract_json(content)

    def test_extract_unified_meals_json_valid(self, service):
        """Test extracting unified meals JSON."""
        content = json.dumps({
            "meals": [
                {"meal_type": "breakfast", "name": "Oatmeal", "calories": 400},
                {"meal_type": "lunch", "name": "Salad", "calories": 500}
            ]
        })
        
        result = service._extract_unified_meals_json(content)
        
        assert "meals" in result
        assert len(result["meals"]) == 2

    def test_extract_unified_meals_json_missing_meals(self, service):
        """Test error when meals array is missing."""
        content = '{"other_data": "value"}'
        
        with pytest.raises(ValueError, match="missing 'meals' array"):
            service._extract_unified_meals_json(content)

    def test_build_unified_meal_prompt(self, service, user_preferences):
        """Test building unified meal prompt."""
        meal_distribution = {
            MealType.BREAKFAST: 500,
            MealType.LUNCH: 700,
            MealType.DINNER: 800
        }
        
        prompt = service._build_unified_meal_prompt(meal_distribution, user_preferences)
        
        assert "breakfast" in prompt.lower()
        assert "lunch" in prompt.lower()
        assert "dinner" in prompt.lower()
        assert "2000" in prompt  # total calories
        assert "vegetarian" in prompt.lower()
        assert "JSON" in prompt

    def test_get_fallback_meal_breakfast(self, service):
        """Test getting fallback breakfast meal."""
        meal = service._get_fallback_meal(MealType.BREAKFAST, 400)
        
        assert meal.meal_type == MealType.BREAKFAST
        assert meal.name is not None
        assert meal.calories > 0
        assert len(meal.ingredients) > 0

    def test_get_fallback_meal_lunch(self, service):
        """Test getting fallback lunch meal."""
        meal = service._get_fallback_meal(MealType.LUNCH, 600)
        
        assert meal.meal_type == MealType.LUNCH
        assert meal.name is not None
        assert meal.calories > 0

    def test_get_fallback_meal_dinner(self, service):
        """Test getting fallback dinner meal."""
        meal = service._get_fallback_meal(MealType.DINNER, 700)
        
        assert meal.meal_type == MealType.DINNER
        assert meal.name is not None
        assert meal.calories > 0

    def test_get_fallback_meal_snack(self, service):
        """Test getting fallback snack meal."""
        meal = service._get_fallback_meal(MealType.SNACK, 200)
        
        assert meal.meal_type == MealType.SNACK
        assert meal.name is not None
        assert meal.calories > 0

    def test_get_fallback_meal_scales_with_calories(self, service):
        """Test that fallback meals scale portions based on calorie target."""
        meal_400 = service._get_fallback_meal(MealType.BREAKFAST, 400)
        meal_800 = service._get_fallback_meal(MealType.BREAKFAST, 800)
        
        # Higher calorie meal should have higher nutrient values
        assert meal_800.calories > meal_400.calories
        assert meal_800.protein > meal_400.protein

    @patch('src.domain.services.daily_meal_suggestion_service.DailyMealSuggestionService._generate_all_meals_unified')
    def test_generate_daily_suggestions_calls_unified(self, mock_unified, service, user_preferences):
        """Test that generate_daily_suggestions uses unified generation."""
        mock_meal = PlannedMeal(
            meal_type=MealType.BREAKFAST,
            name="Test Meal",
            description="Test",
            calories=400,
            protein=20,
            carbs=50,
            fat=10,
            ingredients=["ingredient"],
            instructions=["instruction"]
        )
        mock_unified.return_value = [mock_meal]
        
        result = service.generate_daily_suggestions(user_preferences)
        
        assert len(result) == 1
        assert result[0].name == "Test Meal"
        mock_unified.assert_called_once()

    def test_build_meal_suggestion_prompt_missing_target_calories(self, service):
        """Test error when target_calories is missing."""
        user_preferences = {
            'goal': 'maintenance',
            'dietary_preferences': [],
            'health_conditions': []
        }
        
        with pytest.raises(ValueError, match="target_calories is required"):
            service._build_meal_suggestion_prompt(
                meal_type=MealType.BREAKFAST,
                calorie_target=400,
                user_preferences=user_preferences
            )

    def test_build_meal_suggestion_prompt_with_health_conditions(self, service, user_preferences):
        """Test prompt includes health conditions."""
        user_preferences['health_conditions'] = ['diabetes', 'hypertension']
        
        prompt = service._build_meal_suggestion_prompt(
            meal_type=MealType.LUNCH,
            calorie_target=600,
            user_preferences=user_preferences
        )
        
        assert 'diabetes' in prompt.lower()
        assert 'hypertension' in prompt.lower()

    def test_build_meal_suggestion_prompt_different_goals(self, service, user_preferences):
        """Test prompt adapts to different fitness goals."""
        goals_and_keywords = [
            ('lose_weight', 'low-calorie'),
            ('gain_weight', 'calorie-dense'),
            ('build_muscle', 'protein'),
            ('maintain_weight', 'balanced')
        ]
        
        for goal, keyword in goals_and_keywords:
            user_preferences['goal'] = goal
            prompt = service._build_meal_suggestion_prompt(
                meal_type=MealType.DINNER,
                calorie_target=700,
                user_preferences=user_preferences
            )
            
            assert goal in prompt.lower() or keyword in prompt.lower()

    def test_build_unified_prompt_includes_all_meals(self, service, user_preferences):
        """Test unified prompt includes all meal types."""
        meal_distribution = {
            MealType.BREAKFAST: 500,
            MealType.LUNCH: 700,
            MealType.DINNER: 800
        }
        
        prompt = service._build_unified_meal_prompt(meal_distribution, user_preferences)
        
        # Should have targets for each meal
        assert "Breakfast" in prompt
        assert "Lunch" in prompt
        assert "Dinner" in prompt
        assert "500" in prompt
        assert "700" in prompt
        assert "800" in prompt

    def test_build_unified_prompt_with_dict_macros(self, service):
        """Test unified prompt with dict-format macros."""
        user_preferences = {
            'goal': 'maintenance',
            'activity_level': 'moderate',
            'dietary_preferences': [],
            'health_conditions': [],
            'target_calories': 2000,
            'target_macros': {
                'protein_grams': 150,
                'carbs_grams': 250,
                'fat_grams': 67
            }
        }
        
        meal_distribution = {
            MealType.BREAKFAST: 600,
            MealType.LUNCH: 700,
            MealType.DINNER: 700
        }
        
        prompt = service._build_unified_meal_prompt(meal_distribution, user_preferences)
        
        # Should work with dict format
        assert "protein" in prompt.lower()
        assert prompt is not None

    def test_generate_daily_suggestions_missing_target_calories(self, service):
        """Test error when target_calories is missing from preferences."""
        user_preferences = {
            'goal': 'maintenance',
            'dietary_preferences': []
        }
        
        with pytest.raises(ValueError, match="target_calories is required"):
            service.generate_daily_suggestions(user_preferences)

    def test_calculate_meal_distribution_boundary(self, service):
        """Test meal distribution at boundary threshold."""
        from src.domain.constants import MealDistribution
        
        # Test just below threshold
        distribution_low = service._calculate_meal_distribution(
            MealDistribution.MIN_CALORIES_FOR_SNACK - 1
        )
        assert MealType.SNACK not in distribution_low
        
        # Test just above threshold
        distribution_high = service._calculate_meal_distribution(
            MealDistribution.MIN_CALORIES_FOR_SNACK + 1
        )
        assert MealType.SNACK in distribution_high

    def test_extract_json_with_nested_arrays(self, service):
        """Test extracting JSON with nested arrays."""
        content = '''
        {
            "meals": [
                {
                    "name": "Breakfast",
                    "ingredients": ["item1", "item2", "item3"]
                }
            ]
        }
        '''
        
        result = service._extract_json(content)
        
        assert "meals" in result
        assert len(result["meals"][0]["ingredients"]) == 3

