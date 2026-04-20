"""Tests for GPTResponseParser behavior."""
import pytest


class TestGPTResponseParserFoodLimit:
    def test_caps_food_items_to_max(self, gpt_parser):
        foods = [
            {
                "name": f"Food {i}",
                "quantity": 1,
                "unit": "g",
                "macros": {"protein": 1, "carbs": 2, "fat": 3},
                "confidence": 0.8,
            }
            for i in range(9)
        ]

        gpt_response = {
            "structured_data": {
                "foods": foods,
                "confidence": 0.9,
            }
        }

        nutrition = gpt_parser.parse_to_nutrition(gpt_response)

        assert nutrition.food_items is not None
        assert len(nutrition.food_items) == 8
        assert [item.name for item in nutrition.food_items] == [
            f"Food {i}" for i in range(8)
        ]
        assert nutrition.macros.protein == pytest.approx(8.0)
        assert nutrition.macros.carbs == pytest.approx(16.0)
        assert nutrition.macros.fat == pytest.approx(24.0)
