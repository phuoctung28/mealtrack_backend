"""
Unit tests for RecipeSearchService.
"""
import pytest
import json
from unittest.mock import Mock, MagicMock, patch

from src.domain.services.meal_suggestion.recipe_search_service import (
    RecipeSearchService,
    RecipeSearchCriteria,
    RecipeSearchResult
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
    """Test suite for RecipeSearchService."""

    @pytest.fixture
    def mock_pinecone_service(self):
        """Create a mock Pinecone service."""
        mock = Mock()
        mock_pc = Mock()
        mock_index = Mock()
        mock_pc.Index = Mock(return_value=mock_index)
        mock_pc.inference = Mock()
        mock_pc.inference.embed = Mock(return_value=[{"values": [0.1] * 1024}])
        mock.pc = mock_pc
        return mock

    @pytest.fixture
    def service_with_pinecone(self, mock_pinecone_service):
        """Create service with mocked Pinecone."""
        service = RecipeSearchService(pinecone_service=mock_pinecone_service)
        service.recipes_index = mock_pinecone_service.pc.Index("recipes")
        return service

    @pytest.fixture
    def service_without_pinecone(self):
        """Create service without Pinecone."""
        return RecipeSearchService(pinecone_service=None)

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

    def test_init_with_pinecone_service(self, mock_pinecone_service):
        """Test initialization with Pinecone service."""
        service = RecipeSearchService(pinecone_service=mock_pinecone_service)
        assert service._pinecone == mock_pinecone_service

    def test_init_without_pinecone_service(self):
        """Test initialization without Pinecone service."""
        service = RecipeSearchService(pinecone_service=None)
        assert service._pinecone is None
        assert service.recipes_index is None

    def test_search_recipes_no_index(self, service_without_pinecone, sample_criteria):
        """Test search returns empty when index is not available."""
        results = service_without_pinecone.search_recipes(sample_criteria)
        assert results == []

    def test_search_recipes_basic(self, service_with_pinecone, sample_criteria):
        """Test basic recipe search."""
        # Mock Pinecone query response
        mock_results = {
            "matches": [
                {
                    "score": 0.85,
                    "metadata": {
                        "recipe_id": "recipe_1",
                        "name": "Chicken Rice Bowl",
                        "description": "Delicious chicken and rice",
                        "ingredients": json.dumps([
                            {"name": "chicken", "amount": 150, "unit": "g"},
                            {"name": "rice", "amount": 100, "unit": "g"}
                        ]),
                        "recipe_steps": json.dumps([
                            {"step": 1, "instruction": "Cook chicken", "duration_minutes": 15}
                        ]),
                        "seasonings": json.dumps(["salt", "pepper"]),
                        "calories": 580,
                        "protein": 45,
                        "carbs": 50,
                        "fat": 12,
                        "total_time_minutes": 20,
                        "meal_type": "lunch"
                    }
                }
            ]
        }
        
        service_with_pinecone.recipes_index.query = Mock(return_value=mock_results)
        
        results = service_with_pinecone.search_recipes(sample_criteria)
        
        assert len(results) == 1
        assert isinstance(results[0], RecipeSearchResult)
        assert results[0].recipe_id == "recipe_1"
        assert results[0].name == "Chicken Rice Bowl"
        assert results[0].confidence_score == 0.85

    def test_search_recipes_filters_allergens(self, service_with_pinecone, sample_criteria):
        """Test that recipes with allergens are filtered out."""
        mock_results = {
            "matches": [
                {
                    "score": 0.85,
                    "metadata": {
                        "recipe_id": "recipe_1",
                        "name": "Peanut Chicken",
                        "description": "Chicken with peanuts",
                        "ingredients": json.dumps([
                            {"name": "chicken", "amount": 150, "unit": "g"},
                            {"name": "peanuts", "amount": 30, "unit": "g"}  # Contains allergen
                        ]),
                        "recipe_steps": json.dumps([]),
                        "seasonings": json.dumps([]),
                        "calories": 600,
                        "protein": 40,
                        "carbs": 30,
                        "fat": 20,
                        "total_time_minutes": 20,
                        "meal_type": "lunch"
                    }
                },
                {
                    "score": 0.80,
                    "metadata": {
                        "recipe_id": "recipe_2",
                        "name": "Chicken Rice",
                        "description": "Chicken without allergens",
                        "ingredients": json.dumps([
                            {"name": "chicken", "amount": 150, "unit": "g"},
                            {"name": "rice", "amount": 100, "unit": "g"}
                        ]),
                        "recipe_steps": json.dumps([]),
                        "seasonings": json.dumps([]),
                        "calories": 580,
                        "protein": 45,
                        "carbs": 50,
                        "fat": 12,
                        "total_time_minutes": 20,
                        "meal_type": "lunch"
                    }
                }
            ]
        }
        
        service_with_pinecone.recipes_index.query = Mock(return_value=mock_results)
        
        results = service_with_pinecone.search_recipes(sample_criteria)
        
        # Should filter out recipe with peanuts
        assert len(results) == 1
        assert results[0].recipe_id == "recipe_2"
        assert "peanut" not in results[0].name.lower()

    def test_search_recipes_handles_invalid_json(self, service_with_pinecone, sample_criteria):
        """Test that invalid JSON in metadata is handled gracefully."""
        mock_results = {
            "matches": [
                {
                    "score": 0.85,
                    "metadata": {
                        "recipe_id": "recipe_1",
                        "name": "Test Recipe",
                        "description": "Test",
                        "ingredients": "invalid json",  # Invalid JSON
                        "recipe_steps": json.dumps([]),
                        "seasonings": json.dumps([]),
                        "calories": 600,
                        "protein": 40,
                        "carbs": 30,
                        "fat": 20,
                        "total_time_minutes": 20,
                        "meal_type": "lunch"
                    }
                }
            ]
        }
        
        service_with_pinecone.recipes_index.query = Mock(return_value=mock_results)
        
        results = service_with_pinecone.search_recipes(sample_criteria)
        
        # Should skip recipe with invalid JSON
        assert len(results) == 0

    def test_search_recipes_with_exclude_ids(self, service_with_pinecone, sample_criteria):
        """Test that exclude_ids are passed to Pinecone filter."""
        sample_criteria.exclude_ids = ["recipe_1", "recipe_2"]
        
        service_with_pinecone.recipes_index.query = Mock(return_value={"matches": []})
        
        service_with_pinecone.search_recipes(sample_criteria)
        
        # Verify query was called with exclude filter
        call_args = service_with_pinecone.recipes_index.query.call_args
        assert call_args is not None
        filters = call_args.kwargs.get("filter", {})
        assert "recipe_id" in filters
        assert filters["recipe_id"]["$nin"] == ["recipe_1", "recipe_2"]

    def test_search_recipes_with_max_cook_time(self, service_with_pinecone, sample_criteria):
        """Test that max_cook_time is passed to Pinecone filter."""
        sample_criteria.max_cook_time = 30
        
        service_with_pinecone.recipes_index.query = Mock(return_value={"matches": []})
        
        service_with_pinecone.search_recipes(sample_criteria)
        
        # Verify query was called with time filter
        call_args = service_with_pinecone.recipes_index.query.call_args
        assert call_args is not None
        filters = call_args.kwargs.get("filter", {})
        assert "total_time_minutes" in filters
        assert filters["total_time_minutes"]["$lte"] == 30

    def test_search_recipes_handles_exception(self, service_with_pinecone, sample_criteria):
        """Test that exceptions during search return empty list."""
        service_with_pinecone.recipes_index.query = Mock(side_effect=Exception("Search failed"))
        
        results = service_with_pinecone.search_recipes(sample_criteria)
        
        assert results == []

    def test_embed_query(self, service_with_pinecone):
        """Test query embedding generation."""
        embedding = service_with_pinecone._embed_query("chicken rice lunch")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert all(isinstance(x, (int, float)) for x in embedding)

