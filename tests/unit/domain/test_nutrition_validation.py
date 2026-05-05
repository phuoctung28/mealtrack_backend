"""Unit tests for nutrition domain value objects validation."""

import pytest
from src.domain.model.nutrition.macros import Macros
from src.domain.model.nutrition.nutrition import Nutrition, FoodItem


class TestMacrosValidation:
    def test_valid_macros(self):
        macros = Macros(protein=20, carbs=30, fat=10)
        assert macros.protein == 20
        assert macros.total_calories == 20 * 4 + 30 * 4 + 10 * 9

    def test_negative_protein_raises_error(self):
        with pytest.raises(ValueError, match="protein cannot be negative"):
            Macros(protein=-1, carbs=10, fat=10)

    def test_excessive_value_raises_error(self):
        with pytest.raises(ValueError, match="protein exceeds realistic limit"):
            Macros(protein=6000, carbs=10, fat=10)


class TestFoodItemValidation:
    def test_valid_food_item(self):
        macros = Macros(protein=10, carbs=10, fat=5)
        item = FoodItem(id="123", name="Chicken", quantity=100, unit="g", macros=macros)
        assert item.name == "Chicken"
        # calories is always derived
        assert item.calories == pytest.approx(10 * 4 + 10 * 4 + 5 * 9)

    def test_empty_name_raises_error(self):
        macros = Macros(protein=10, carbs=10, fat=5)
        with pytest.raises(ValueError, match="Food item name cannot be empty"):
            FoodItem(id="1", name="", quantity=10, unit="g", macros=macros)

    def test_calories_no_longer_accepted_as_kwarg(self):
        """FoodItem no longer accepts calories= — it is a derived property."""
        macros = Macros(protein=10, carbs=10, fat=5)
        with pytest.raises(TypeError):
            FoodItem(
                id="1", name="Test", quantity=10, unit="g", calories=10, macros=macros
            )


class TestNutritionValidation:
    def test_valid_nutrition(self):
        macros = Macros(protein=20, carbs=20, fat=10)
        nut = Nutrition(macros=macros)
        # calories derived: 20*4 + 20*4 + 10*9 = 250
        assert nut.calories == pytest.approx(250.0)

    def test_calories_no_longer_accepted_as_kwarg(self):
        """Nutrition no longer accepts calories= — it is a derived property."""
        macros = Macros(protein=20, carbs=20, fat=10)
        with pytest.raises(TypeError):
            Nutrition(calories=-100, macros=macros)

    def test_calories_always_non_negative(self):
        """Calories derived from macros are always >= 0 because macros are >= 0."""
        macros = Macros(protein=0, carbs=0, fat=0)
        nut = Nutrition(macros=macros)
        assert nut.calories == 0.0
