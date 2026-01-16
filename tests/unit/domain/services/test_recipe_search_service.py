"""
Unit tests for RecipeSearchService.
"""
import json
from unittest.mock import Mock, patch

import pytest

from src.domain.services.meal_suggestion.recipe_search_service import RecipeSearchService
from src.domain.ports.recipe_search_port import (
    RecipeSearchCriteria,
    RecipeSearchResult,
)


@pytest.mark.unit
class TestRecipeSearchCriteria:
    """Test suite for RecipeSearchCriteria."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        criteria = RecipeSearchCriteria(
            meal_type="lunch",
            target_calories=600
        )
        
        assert criteria.meal_type == "lunch"
        assert criteria.target_calories == 600
        assert criteria.calorie_tolerance == 100
        assert criteria.max_cook_time is None
        assert criteria.dietary_preferences == []
        assert criteria.allergies == []
        assert criteria.ingredients == []
        assert criteria.exclude_ids == []

    def test_init_with_all_fields(self):
        """Test initialization with all fields."""
        criteria = RecipeSearchCriteria(
            meal_type="dinner",
            target_calories=800,
            calorie_tolerance=150,
            max_cook_time=30,
            dietary_preferences=["vegetarian"],
            allergies=["nuts"],
            ingredients=["chicken", "rice"],
            exclude_ids=["recipe_1", "recipe_2"]
        )
        
        assert criteria.meal_type == "dinner"
        assert criteria.target_calories == 800
        assert criteria.calorie_tolerance == 150
        assert criteria.max_cook_time == 30
        assert criteria.dietary_preferences == ["vegetarian"]
        assert criteria.allergies == ["nuts"]
        assert criteria.ingredients == ["chicken", "rice"]
        assert criteria.exclude_ids == ["recipe_1", "recipe_2"]


@pytest.mark.unit
class TestRecipeSearchService:
    """Test suite for RecipeSearchService using the RecipeSearchPort abstraction."""

    @pytest.fixture
    def mock_search_port(self):
        """Create a mock implementation of RecipeSearchPort."""
        mock = Mock()
        mock.search_recipes = Mock()
        mock.get_recipe_by_id = Mock()
        return mock

    @pytest.fixture
    def service_with_port(self, mock_search_port):
        """Create service with injected search port."""
        return RecipeSearchService(search_port=mock_search_port)

    @pytest.fixture
    def service_without_port(self):
        """Create service without an injected port (will try adapter and handle failures)."""
        return RecipeSearchService(search_port=None)

    @pytest.fixture
    def sample_criteria(self):
        """Create sample search criteria."""
        return RecipeSearchCriteria(
            meal_type="lunch",
            target_calories=600,
            ingredients=["chicken", "rice"],
            dietary_preferences=["high-protein"],
            allergies=["peanuts"]
        )

    def test_init_with_search_port(self, mock_search_port):
        """Service should keep reference to injected search port."""
        service = RecipeSearchService(search_port=mock_search_port)
        assert service._search_port is mock_search_port

    def test_search_recipes_no_adapter(self, service_without_port, sample_criteria):
        """If adapter initialization fails, search_recipes should return empty list."""
        # Since the adapter module doesn't exist, the import will fail and return empty list
        results = service_without_port.search_recipes(sample_criteria)
        assert results == []

    def test_search_recipes_delegates_to_port(self, service_with_port, mock_search_port, sample_criteria):
        """search_recipes should delegate to the injected search port."""
        expected = [
            RecipeSearchResult(
                recipe_id="recipe_1",
                name="Chicken Rice Bowl",
                calories=600,
                cook_time=30,
                ingredients=["chicken", "rice"],
                instructions=["Cook chicken", "Serve with rice"],
                score=0.85,
            )
        ]
        mock_search_port.search_recipes.return_value = expected

        results = service_with_port.search_recipes(sample_criteria)

        assert results == expected
        mock_search_port.search_recipes.assert_called_once_with(sample_criteria, 10)

    def test_get_recipe_by_id_delegates_to_port(self, service_with_port, mock_search_port):
        """get_recipe_by_id should delegate to the injected search port."""
        expected = RecipeSearchResult(
            recipe_id="recipe_42",
            name="Test Recipe",
            calories=500,
            cook_time=25,
            ingredients=["a"],
            instructions=["b"],
            score=0.9,
        )
        mock_search_port.get_recipe_by_id.return_value = expected

        result = service_with_port.get_recipe_by_id("recipe_42")

        assert result == expected
        mock_search_port.get_recipe_by_id.assert_called_once_with("recipe_42")

    def test_get_recipe_by_id_no_adapter(self, service_without_port):
        """If adapter initialization fails, get_recipe_by_id should return None."""
        # Since the adapter module doesn't exist, the import will fail and return None
        result = service_without_port.get_recipe_by_id("recipe_42")
        assert result is None

