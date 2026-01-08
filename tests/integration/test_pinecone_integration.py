"""
Integration tests for Pinecone meal nutrition flow.
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.infra.services.pinecone_service import PineconeNutritionService


def _pinecone_indexes_available():
    """Check if Pinecone indexes are actually available."""
    if not os.getenv("PINECONE_API_KEY"):
        return False
    try:
        from src.infra.services.pinecone_service import PineconeNutritionService

        service = PineconeNutritionService()
        return service.ingredients_index is not None or service.usda_index is not None
    except (ValueError, Exception):
        return False


@pytest.mark.integration
@pytest.mark.skipif(
    not _pinecone_indexes_available(),
    reason="Pinecone indexes not available (no 'ingredients' or 'usda' index)",
)
class TestPineconeLiveIntegration:
    """
    Live integration tests with actual Pinecone indexes.

    These tests require:
    - PINECONE_API_KEY environment variable
    - Existing 'ingredients' and/or 'usda' indexes in Pinecone

    Skip if running in CI without Pinecone access.
    """

    def test_connect_to_pinecone_indexes(self):
        """Test connection to live Pinecone indexes."""
        # Act
        service = PineconeNutritionService()

        # Assert
        assert service.ingredients_index is not None or service.usda_index is not None

    def test_search_common_ingredient(self):
        """Test searching for a common ingredient."""
        # Arrange
        service = PineconeNutritionService()

        # Act
        result = service.search_ingredient("chicken breast")

        # Assert
        assert result is not None
        assert "name" in result
        assert "calories" in result
        assert "protein" in result
        assert result["score"] > 0.3  # Reasonable similarity score

        print(f"Found: {result['name']} ({result['score']:.2%} match)")
        print(f"Nutrition: {result['calories']} cal, {result['protein']}g protein")

    def test_get_scaled_nutrition_for_portion(self):
        """Test getting nutrition scaled to specific portion."""
        # Arrange
        service = PineconeNutritionService()

        # Act
        result = service.get_scaled_nutrition("rice", 150, "g")

        # Assert
        assert result is not None
        assert result.serving_size_g == 150
        assert result.calories > 0
        assert result.protein >= 0

        print(f"150g rice: {result.calories:.0f} cal, {result.protein:.1f}g protein")

    def test_calculate_meal_nutrition(self):
        """Test calculating total nutrition for a complete meal."""
        # Arrange
        service = PineconeNutritionService()
        ingredients = [
            {"name": "chicken breast", "quantity": 200, "unit": "g"},
            {"name": "rice", "quantity": 150, "unit": "g"},
            {"name": "broccoli", "quantity": 100, "unit": "g"},
        ]

        # Act
        total = service.calculate_total_nutrition(ingredients)

        # Assert
        assert total.calories > 0
        assert total.protein > 0
        assert total.serving_size_g == 450  # 200 + 150 + 100

        print(f"\nMeal (450g total):")
        print(f"  Calories: {total.calories:.0f} kcal")
        print(f"  Protein: {total.protein:.1f}g")
        print(f"  Carbs: {total.carbs:.1f}g")
        print(f"  Fat: {total.fat:.1f}g")


@pytest.mark.integration
@pytest.mark.skipif(
    not _pinecone_indexes_available(),
    reason="Pinecone indexes not available - skipping Pinecone mock integration tests",
)
class TestPineconeMockIntegration:
    """
    Integration tests with mocked Pinecone for consistent CI testing.
    """

    @patch("src.infra.services.pinecone_service.Pinecone")
    def test_full_meal_calculation_flow(self, mock_pinecone):
        """Test complete flow from search to nutrition calculation."""
        # Arrange - Mock Pinecone responses
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_ingredients_index = Mock()

        # Mock Pinecone Inference API
        mock_pc.inference.embed.return_value = [
            {"values": [0.1] * 384}  # 384-dim embedding
        ]

        def mock_query(vector, top_k, include_metadata):
            """Return different ingredients based on embedding."""
            # In real scenario, embeddings would be different for each query
            # For testing, we'll use a simple counter
            if not hasattr(mock_query, "call_count"):
                mock_query.call_count = 0

            mock_query.call_count += 1

            if mock_query.call_count == 1:  # First call - chicken
                return {
                    "matches": [
                        {
                            "score": 0.85,
                            "metadata": {
                                "name": "Chicken Breast",
                                "calories": 165,
                                "protein": 31,
                                "fat": 3.6,
                                "carbs": 0,
                                "fiber": 0,
                                "sugar": 0,
                                "sodium": 74,
                            },
                        }
                    ]
                }
            elif mock_query.call_count == 2:  # Second call - rice
                return {
                    "matches": [
                        {
                            "score": 0.80,
                            "metadata": {
                                "name": "White Rice Cooked",
                                "calories": 130,
                                "protein": 2.7,
                                "fat": 0.3,
                                "carbs": 28,
                                "fiber": 0.4,
                                "sugar": 0.1,
                                "sodium": 1,
                            },
                        }
                    ]
                }
            elif mock_query.call_count == 3:  # Third call - broccoli
                return {
                    "matches": [
                        {
                            "score": 0.90,
                            "metadata": {
                                "name": "Broccoli Raw",
                                "calories": 34,
                                "protein": 2.8,
                                "fat": 0.4,
                                "carbs": 7,
                                "fiber": 2.6,
                                "sugar": 1.7,
                                "sodium": 33,
                            },
                        }
                    ]
                }

        mock_ingredients_index.query.side_effect = mock_query
        mock_pc.Index.return_value = mock_ingredients_index

        # Act - Calculate meal nutrition
        service = PineconeNutritionService(pinecone_api_key="test-key")
        ingredients = [
            {"name": "chicken breast", "quantity": 200, "unit": "g"},
            {"name": "rice", "quantity": 150, "unit": "g"},
            {"name": "broccoli", "quantity": 100, "unit": "g"},
        ]
        total = service.calculate_total_nutrition(ingredients)

        # Assert
        # Chicken: 165 * 2 = 330
        # Rice: 130 * 1.5 = 195
        # Broccoli: 34 * 1 = 34
        # Total: 559 calories
        assert total.calories == pytest.approx(559, 0.1)

        # Chicken: 31 * 2 = 62
        # Rice: 2.7 * 1.5 = 4.05
        # Broccoli: 2.8 * 1 = 2.8
        # Total: 68.85g protein
        assert total.protein == pytest.approx(68.85, 0.1)

        # Total weight
        assert total.serving_size_g == 450

        # Verify all ingredients were searched
        assert mock_ingredients_index.query.call_count == 3

    @patch("src.infra.services.pinecone_service.Pinecone")
    def test_unit_conversion_in_flow(self, mock_pinecone):
        """Test that unit conversions work properly in the flow."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_index = Mock()

        # Mock Pinecone Inference API
        mock_pc.inference.embed.return_value = [
            {"values": [0.1] * 384}  # 384-dim embedding
        ]

        mock_index.query.return_value = {
            "matches": [
                {
                    "score": 0.85,
                    "metadata": {
                        "name": "Oats",
                        "calories": 389,
                        "protein": 16.9,
                        "fat": 6.9,
                        "carbs": 66.3,
                        "fiber": 10.6,
                        "sugar": 0,
                        "sodium": 2,
                    },
                }
            ]
        }

        mock_pc.Index.return_value = mock_index

        service = PineconeNutritionService(pinecone_api_key="test-key")

        # Act - Request 1 cup of oats (240g)
        result = service.get_scaled_nutrition("oats", 1, "cup")

        # Assert
        # 1 cup = 240g = 2.4 * 100g
        # Calories: 389 * 2.4 = 933.6
        assert result.serving_size_g == 240
        assert result.calories == pytest.approx(933.6, 0.1)
        assert result.protein == pytest.approx(40.56, 0.1)  # 16.9 * 2.4
