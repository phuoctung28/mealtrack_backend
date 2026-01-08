"""
Unit tests for consolidated SuggestionService.
"""
import pytest
from datetime import datetime, date
from unittest.mock import Mock

from src.domain.services.suggestion.suggestion_service import SuggestionService
from src.domain.model.meal_planning import MealType


@pytest.fixture
def service():
    """Create SuggestionService instance."""
    return SuggestionService()


@pytest.fixture
def mock_suggestions():
    """Create mock meal suggestions."""
    def make_suggestion(name, calories, prep_time, ingredients):
        return Mock(
            meal_name=name,
            macros=Mock(calories=calories),
            prep_time_minutes=prep_time,
            ingredients=[Mock(name=ing) for ing in ingredients],
            confidence_score=0.85,
        )
    
    return [
        make_suggestion("Chicken Salad", 450, 15, ["chicken", "lettuce"]),
        make_suggestion("Beef Stir Fry", 550, 25, ["beef", "vegetables"]),
        make_suggestion("Veggie Bowl", 400, 20, ["tofu", "rice", "vegetables"]),
        make_suggestion("Salmon Plate", 500, 30, ["salmon", "asparagus"]),
    ]


class TestMealTypeRecommendation:
    """Test meal type recommendation."""

    def test_get_recommended_meal_type_morning(self, service):
        """Morning time should recommend breakfast."""
        morning = datetime(2024, 1, 15, 8, 0)
        result = service.get_recommended_meal_type(morning)
        assert result == MealType.BREAKFAST

    def test_get_recommended_meal_type_noon(self, service):
        """Noon time should recommend lunch."""
        noon = datetime(2024, 1, 15, 12, 30)
        result = service.get_recommended_meal_type(noon)
        assert result == MealType.LUNCH


class TestDailySuggestionContext:
    """Test daily suggestion context generation."""

    def test_get_daily_suggestion_context(self, service):
        """Should return complete context dictionary."""
        context = service.get_daily_suggestion_context(
            user_id="user123",
            daily_calories=2000,
        )
        
        assert context["user_id"] == "user123"
        assert context["daily_calories"] == 2000
        assert "current_meal_type" in context
        assert "remaining_meals" in context
        assert "distributions" in context


class TestPreferenceFiltering:
    """Test suggestion filtering by preferences."""

    def test_filter_by_prep_time(self, service, mock_suggestions):
        """Should filter suggestions by max prep time."""
        filtered = service.filter_suggestions_by_preferences(
            mock_suggestions,
            max_prep_time=20,
        )
        
        # Only suggestions with prep_time <= 20 should remain
        assert len(filtered) == 2
        for s in filtered:
            assert s.prep_time_minutes <= 20

    def test_filter_by_allergies(self, service, mock_suggestions):
        """Should filter out suggestions with allergens."""
        filtered = service.filter_suggestions_by_preferences(
            mock_suggestions,
            allergies=["chicken", "beef"],
        )
        
        # Chicken Salad and Beef Stir Fry should be filtered out
        assert len(filtered) == 2
        names = [s.meal_name for s in filtered]
        assert "Chicken Salad" not in names
        assert "Beef Stir Fry" not in names

    def test_filter_vegetarian(self, service, mock_suggestions):
        """Should filter for vegetarian options."""
        filtered = service.filter_suggestions_by_preferences(
            mock_suggestions,
            dietary_preferences=["vegetarian"],
        )
        
        # Only Veggie Bowl should remain (no meat)
        assert len(filtered) == 1
        assert filtered[0].meal_name == "Veggie Bowl"


class TestSuggestionScoring:
    """Test suggestion scoring."""

    def test_calculate_suggestion_score_calorie_match(self, service):
        """Score should be higher for better calorie match."""
        suggestion = Mock(
            macros=Mock(calories=500),
            confidence_score=0.8,
            prep_time_minutes=20,
        )
        
        # Exact match
        score_exact = service.calculate_suggestion_score(suggestion, 500)
        
        # 100 calorie difference
        score_diff = service.calculate_suggestion_score(suggestion, 600)
        
        assert score_exact > score_diff

    def test_calculate_suggestion_score_bounds(self, service):
        """Score should be between 0 and 1."""
        suggestion = Mock(
            macros=Mock(calories=500),
            confidence_score=0.5,
            prep_time_minutes=20,
        )
        
        score = service.calculate_suggestion_score(suggestion, 500)
        
        assert 0.0 <= score <= 1.0
