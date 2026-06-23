"""Tests for GPTResponseParser behavior."""

import pytest

from src.domain.parsers.gpt_response_parser import GPTResponseParsingError


class TestGPTResponseParserFoodLimit:
    def test_rejects_food_items_over_max(self, gpt_parser):
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

        with pytest.raises(GPTResponseParsingError):
            gpt_parser.parse_to_nutrition(gpt_response)


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


class TestGPTResponseParserOptionalFoods:
    def test_parse_to_nutrition_allows_missing_foods_with_macros(self, gpt_parser):
        gpt_response = {
            "structured_data": {
                "dish_name": "Macro Meal",
                "macros": {"protein": 20, "carbs": 40, "fat": 10},
            }
        }

        nutrition = gpt_parser.parse_to_nutrition(gpt_response)

        assert nutrition.food_items is None
        assert nutrition.macros.protein == pytest.approx(20.0)
        assert nutrition.macros.carbs == pytest.approx(40.0)
        assert nutrition.macros.fat == pytest.approx(10.0)
        assert nutrition.confidence_score == pytest.approx(0.5)

    def test_parse_to_nutrition_allows_empty_foods_with_macros(self, gpt_parser):
        gpt_response = {
            "structured_data": {
                "dish_name": "Macro Meal",
                "foods": [],
                "macros": {"protein": 10, "carbs": 20, "fat": 5},
                "confidence": 0.8,
            }
        }

        nutrition = gpt_parser.parse_to_nutrition(gpt_response)

        assert nutrition.food_items is None
        assert nutrition.macros.protein == pytest.approx(10.0)
        assert nutrition.macros.carbs == pytest.approx(20.0)
        assert nutrition.macros.fat == pytest.approx(5.0)
        assert nutrition.confidence_score == pytest.approx(0.8)

    def test_parse_to_nutrition_clamps_top_level_confidence(self, gpt_parser):
        gpt_response = {
            "structured_data": {
                "foods": [
                    {
                        "name": "Food 0",
                        "quantity": 1,
                        "unit": "g",
                        "macros": {"protein": 1, "carbs": 2, "fat": 3},
                    }
                ],
                "confidence": 1.2,
            }
        }

        nutrition = gpt_parser.parse_to_nutrition(gpt_response)

        assert nutrition.confidence_score == pytest.approx(1.0)


class TestGPTResponseParserFoodGuard:
    def test_parse_is_food_defaults_true_when_missing(self, gpt_parser):
        gpt_response = {"structured_data": {"dish_name": "Rice Bowl"}}

        assert gpt_parser.parse_is_food(gpt_response) is True

    def test_parse_is_food_returns_false_for_boolean_false(self, gpt_parser):
        gpt_response = {"structured_data": {"is_food": False}}

        assert gpt_parser.parse_is_food(gpt_response) is False

    def test_parse_is_food_returns_false_for_string_false(self, gpt_parser):
        gpt_response = {"structured_data": {"is_food": "false"}}

        assert gpt_parser.parse_is_food(gpt_response) is False

    def test_parse_is_food_returns_false_for_numeric_zero(self, gpt_parser):
        gpt_response = {"structured_data": {"is_food": 0}}

        assert gpt_parser.parse_is_food(gpt_response) is False

    def test_parse_is_food_defaults_true_when_structured_data_missing(self, gpt_parser):
        assert gpt_parser.parse_is_food({}) is True


class TestGPTResponseParserStrictSchemaMode:
    def test_non_strict_mode_allows_non_list_foods_with_top_level_macros(self):
        from src.domain.parsers.gpt_response_parser import GPTResponseParser

        parser = GPTResponseParser(strict_schema_mode=False)
        gpt_response = {
            "structured_data": {
                "dish_name": "Macro Meal",
                "foods": "invalid-shape",
                "macros": {"protein": 12, "carbs": 30, "fat": 7},
            }
        }

        nutrition = parser.parse_to_nutrition(gpt_response)

        assert nutrition.food_items is None
        assert nutrition.macros.protein == pytest.approx(12.0)
        assert nutrition.macros.carbs == pytest.approx(30.0)
        assert nutrition.macros.fat == pytest.approx(7.0)


class TestGPTResponseParserZeroQuantity:
    def test_rejects_zero_quantity_food_items(self, gpt_parser):
        """AI quantity=0 should fail validation instead of producing partial meals."""
        gpt_response = {
            "structured_data": {
                "dish_name": "Mixed Plate",
                "foods": [
                    {
                        "name": "Valid Food",
                        "quantity": 100,
                        "unit": "g",
                        "macros": {"protein": 10, "carbs": 20, "fat": 5},
                    },
                    {
                        "name": "Zero Quantity Food",
                        "quantity": 0,
                        "unit": "g",
                        "macros": {"protein": 5, "carbs": 10, "fat": 2},
                    },
                    {
                        "name": "Another Valid Food",
                        "quantity": 50,
                        "unit": "g",
                        "macros": {"protein": 8, "carbs": 15, "fat": 3},
                    },
                ],
                "confidence": 0.9,
            }
        }

        with pytest.raises(GPTResponseParsingError):
            gpt_parser.parse_to_nutrition(gpt_response)

    def test_rejects_negative_quantity_food_items(self, gpt_parser):
        """Negative quantities should fail validation."""
        gpt_response = {
            "structured_data": {
                "dish_name": "Test Meal",
                "foods": [
                    {
                        "name": "Negative Quantity",
                        "quantity": -5,
                        "unit": "g",
                        "macros": {"protein": 5, "carbs": 10, "fat": 2},
                    },
                    {
                        "name": "Valid Food",
                        "quantity": 100,
                        "unit": "g",
                        "macros": {"protein": 10, "carbs": 20, "fat": 5},
                    },
                ],
                "confidence": 0.9,
            }
        }

        with pytest.raises(GPTResponseParsingError):
            gpt_parser.parse_to_nutrition(gpt_response)

    def test_rejects_over_max_quantity_food_items(self, gpt_parser):
        """Impossible AI quantities should fail validation."""
        gpt_response = {
            "structured_data": {
                "dish_name": "Mixed Plate",
                "foods": [
                    {
                        "name": "Valid Food",
                        "quantity": 100,
                        "unit": "g",
                        "macros": {"protein": 10, "carbs": 20, "fat": 5},
                    },
                    {
                        "name": "Impossible Quantity",
                        "quantity": 150000,
                        "unit": "g",
                        "macros": {"protein": 500, "carbs": 1000, "fat": 200},
                    },
                ],
                "confidence": 0.9,
            }
        }

        with pytest.raises(GPTResponseParsingError):
            gpt_parser.parse_to_nutrition(gpt_response)


class TestGPTResponseParserQuantityGMapping:
    def test_valid_quantity_maps_to_food_item_with_grams_unit(self, gpt_parser):
        """quantity=100 (from legacy vision payload, converted from quantity_g=100) maps to FoodItem(quantity=100, unit='g')."""
        gpt_response = {
            "structured_data": {
                "dish_name": "Grilled Chicken",
                "foods": [
                    {
                        "name": "Chicken breast",
                        "quantity": 100,
                        "unit": "g",
                        "macros": {"protein": 30.0, "carbs": 0.0, "fat": 6.0},
                        "confidence": 0.9,
                    }
                ],
                "confidence": 0.85,
            }
        }

        nutrition = gpt_parser.parse_to_nutrition(gpt_response)

        assert nutrition.food_items is not None
        assert len(nutrition.food_items) == 1
        item = nutrition.food_items[0]
        assert item.quantity == pytest.approx(100.0)
        assert item.unit == "g"

    def test_calories_derived_from_macros_not_from_ai_field(self, gpt_parser):
        """Calories must come from macro arithmetic, never from AI-provided kcal field."""
        gpt_response = {
            "structured_data": {
                "dish_name": "Test Meal",
                "foods": [
                    {
                        "name": "Rice",
                        "quantity": 100,
                        "unit": "g",
                        "macros": {"protein": 3.0, "carbs": 28.0, "fat": 0.5},
                    }
                ],
                "kcal": 99999,
                "confidence": 0.9,
            }
        }

        nutrition = gpt_parser.parse_to_nutrition(gpt_response)
        # Calories = protein*4 + carbs*4 + fat*9 = 3*4 + 28*4 + 0.5*9 = 12 + 112 + 4.5 = 128.5
        assert nutrition.calories == pytest.approx(128.5, abs=1.0)
        assert nutrition.calories < 500
