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
                "dish_name": "Test Dish",
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


class TestGPTResponseParserDishNameCompatibility:
    def test_parse_to_nutrition_allows_missing_dish_name(self, gpt_parser):
        gpt_response = {
            "structured_data": {
                "foods": [
                    {
                        "name": "Food 0",
                        "quantity": 1,
                        "unit": "g",
                        "macros": {"protein": 1, "carbs": 2, "fat": 3},
                        "confidence": 0.8,
                    }
                ],
                "confidence": 0.9,
            }
        }

        nutrition = gpt_parser.parse_to_nutrition(gpt_response)

        assert nutrition.food_items is not None
        assert len(nutrition.food_items) == 1
        assert nutrition.food_items[0].name == "Food 0"
        assert nutrition.macros.protein == pytest.approx(1.0)
        assert nutrition.macros.carbs == pytest.approx(2.0)
        assert nutrition.macros.fat == pytest.approx(3.0)
