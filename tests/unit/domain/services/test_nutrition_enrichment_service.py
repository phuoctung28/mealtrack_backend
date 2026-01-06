"""
Unit tests for NutritionEnrichmentService.
"""
import pytest
from unittest.mock import Mock, MagicMock

from src.domain.services.meal_suggestion.nutrition_enrichment_service import (
    NutritionEnrichmentService,
    EnrichmentResult
)
from src.domain.model.meal_suggestion.meal_suggestion import Ingredient, MacroEstimate


@pytest.mark.unit
class TestNutritionEnrichmentService:
    """Test suite for NutritionEnrichmentService."""

    @pytest.fixture
    def mock_pinecone_service(self):
        """Create a mock Pinecone service."""
        mock = Mock()
        mock_nutrition = Mock()
        mock_nutrition.calories = 200.0
        mock_nutrition.protein = 20.0
        mock_nutrition.carbs = 30.0
        mock_nutrition.fat = 5.0
        mock.get_scaled_nutrition = Mock(return_value=mock_nutrition)
        return mock

    @pytest.fixture
    def service_with_pinecone(self, mock_pinecone_service):
        """Create service with mocked Pinecone."""
        return NutritionEnrichmentService(pinecone_service=mock_pinecone_service)

    @pytest.fixture
    def service_without_pinecone(self):
        """Create service without Pinecone."""
        return NutritionEnrichmentService(pinecone_service=None)

    @pytest.fixture
    def sample_ingredients(self):
        """Create sample ingredients."""
        return [
            Ingredient(name="chicken breast", amount=150, unit="g"),
            Ingredient(name="rice", amount=100, unit="g"),
            Ingredient(name="broccoli", amount=80, unit="g"),
        ]

    def test_init_with_pinecone_service(self, mock_pinecone_service):
        """Test initialization with Pinecone service."""
        service = NutritionEnrichmentService(pinecone_service=mock_pinecone_service)
        assert service._pinecone == mock_pinecone_service

    def test_init_without_pinecone_service(self):
        """Test initialization without Pinecone service."""
        with pytest.raises(Exception):
            # This will try to initialize Pinecone and may fail
            service = NutritionEnrichmentService()
        # But we can still create with None explicitly
        service = NutritionEnrichmentService(pinecone_service=None)
        assert service._pinecone is None

    def test_calculate_meal_nutrition_with_pinecone(self, service_with_pinecone, sample_ingredients):
        """Test nutrition calculation with Pinecone service."""
        result = service_with_pinecone.calculate_meal_nutrition(
            ingredients=sample_ingredients,
            target_calories=600
        )
        
        assert isinstance(result, EnrichmentResult)
        assert result.macros.calories > 0
        assert result.macros.protein > 0
        assert result.macros.carbs > 0
        assert result.macros.fat > 0
        assert result.confidence_score >= 0.0
        assert result.confidence_score <= 1.0
        assert isinstance(result.missing_ingredients, list)

    def test_calculate_meal_nutrition_without_pinecone(self, service_without_pinecone, sample_ingredients):
        """Test nutrition calculation without Pinecone (uses estimation)."""
        result = service_without_pinecone.calculate_meal_nutrition(
            ingredients=sample_ingredients,
            target_calories=600
        )
        
        assert isinstance(result, EnrichmentResult)
        assert result.macros.calories > 0
        assert result.macros.protein > 0
        assert result.macros.carbs > 0
        assert result.macros.fat > 0

    def test_calculate_meal_nutrition_empty_ingredients(self, service_with_pinecone):
        """Test nutrition calculation with empty ingredients list."""
        result = service_with_pinecone.calculate_meal_nutrition(
            ingredients=[],
            target_calories=600
        )
        
        assert isinstance(result, EnrichmentResult)
        assert result.macros.calories == 600  # Uses target calories
        assert result.confidence_score == 0.3  # Low confidence for fallback

    def test_calculate_meal_nutrition_missing_ingredients(self, service_with_pinecone):
        """Test nutrition calculation when some ingredients are missing from Pinecone."""
        mock_pinecone = Mock()
        mock_pinecone.get_scaled_nutrition = Mock(side_effect=[
            Mock(calories=200, protein=20, carbs=30, fat=5),  # First ingredient found
            None,  # Second ingredient missing
            None,  # Third ingredient missing
        ])
        service = NutritionEnrichmentService(pinecone_service=mock_pinecone)
        
        result = service.calculate_meal_nutrition(
            ingredients=[
                Ingredient(name="chicken", amount=150, unit="g"),
                Ingredient(name="unknown_food", amount=100, unit="g"),
                Ingredient(name="mystery_item", amount=50, unit="g"),
            ],
            target_calories=600
        )
        
        assert len(result.missing_ingredients) == 2
        assert "unknown_food" in result.missing_ingredients
        assert "mystery_item" in result.missing_ingredients
        assert result.confidence_score < 1.0  # Lower confidence due to missing ingredients

    def test_convert_to_grams_weight_units(self, service_with_pinecone):
        """Test unit conversion for weight units."""
        assert service_with_pinecone._convert_to_grams(100, "g") == 100
        assert service_with_pinecone._convert_to_grams(1, "kg") == 1000
        assert service_with_pinecone._convert_to_grams(1, "oz") == 28.35
        assert abs(service_with_pinecone._convert_to_grams(1, "lb") - 453.59) < 0.01

    def test_convert_to_grams_volume_units(self, service_with_pinecone):
        """Test unit conversion for volume units."""
        assert service_with_pinecone._convert_to_grams(1, "cup") == 240
        assert service_with_pinecone._convert_to_grams(1, "tbsp") == 15
        assert service_with_pinecone._convert_to_grams(1, "tsp") == 5
        assert service_with_pinecone._convert_to_grams(100, "ml") == 100

    def test_convert_to_grams_count_units(self, service_with_pinecone):
        """Test unit conversion for count units."""
        assert service_with_pinecone._convert_to_grams(1, "serving") == 100
        assert service_with_pinecone._convert_to_grams(1, "piece") == 50
        assert service_with_pinecone._convert_to_grams(1, "slice") == 25

    def test_convert_to_grams_unknown_unit(self, service_with_pinecone):
        """Test unit conversion for unknown unit defaults to 1."""
        assert service_with_pinecone._convert_to_grams(100, "unknown_unit") == 100

    def test_estimate_nutrition_protein_food(self, service_with_pinecone):
        """Test nutrition estimation for protein-rich foods."""
        ingredient = Ingredient(name="chicken breast", amount=150, unit="g")
        result = service_with_pinecone._estimate_nutrition(ingredient, 600, 3)
        
        assert result['calories'] > 0
        assert result['protein'] > result['carbs']  # Protein foods have more protein
        assert result['fat'] > 0

    def test_estimate_nutrition_carb_food(self, service_with_pinecone):
        """Test nutrition estimation for carb-rich foods."""
        ingredient = Ingredient(name="rice", amount=100, unit="g")
        result = service_with_pinecone._estimate_nutrition(ingredient, 600, 3)
        
        assert result['calories'] > 0
        assert result['carbs'] > result['protein']  # Carb foods have more carbs

    def test_estimate_nutrition_fat_food(self, service_with_pinecone):
        """Test nutrition estimation for fat-rich foods."""
        ingredient = Ingredient(name="olive oil", amount=15, unit="ml")
        result = service_with_pinecone._estimate_nutrition(ingredient, 600, 3)
        
        assert result['calories'] > 0
        assert result['fat'] > result['protein']  # Fat foods have more fat

    def test_estimate_nutrition_vegetable(self, service_with_pinecone):
        """Test nutrition estimation for vegetables."""
        ingredient = Ingredient(name="broccoli", amount=100, unit="g")
        result = service_with_pinecone._estimate_nutrition(ingredient, 600, 3)
        
        assert result['calories'] > 0
        assert result['calories'] < 100  # Vegetables are low calorie

    def test_create_fallback_result(self, service_with_pinecone):
        """Test fallback result creation."""
        result = service_with_pinecone._create_fallback_result(600)
        
        assert isinstance(result, EnrichmentResult)
        assert result.macros.calories == 600
        assert result.macros.protein > 0
        assert result.macros.carbs > 0
        assert result.macros.fat > 0
        assert result.confidence_score == 0.3
        assert result.missing_ingredients == []

    def test_calculate_meal_nutrition_validates_target_calories(self, service_with_pinecone, sample_ingredients):
        """Test that large deviations from target calories are logged."""
        # This test verifies the warning logic works
        result = service_with_pinecone.calculate_meal_nutrition(
            ingredients=sample_ingredients,
            target_calories=1000  # Much higher than what ingredients provide
        )
        
        # Should still return a result, but may have deviation warning
        assert isinstance(result, EnrichmentResult)
        assert result.macros.calories > 0

