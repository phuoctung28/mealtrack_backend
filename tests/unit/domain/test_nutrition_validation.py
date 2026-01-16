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
        item = FoodItem(
            id="123",
            name="Chicken",
            quantity=100,
            unit="g",
            calories=150,
            macros=macros
        )
        assert item.name == "Chicken"

    def test_empty_name_raises_error(self):
        macros = Macros(protein=10, carbs=10, fat=5)
        with pytest.raises(ValueError, match="Food item name cannot be empty"):
            FoodItem(id="1", name="", quantity=10, unit="g", calories=10, macros=macros)

    def test_negative_calories_raises_error(self):
        macros = Macros(protein=10, carbs=10, fat=5)
        with pytest.raises(ValueError, match="Calories cannot be negative"):
            FoodItem(id="1", name="Test", quantity=10, unit="g", calories=-5, macros=macros)

class TestNutritionValidation:
    def test_valid_nutrition(self):
        macros = Macros(protein=20, carbs=20, fat=10)
        nut = Nutrition(calories=250, macros=macros)
        assert nut.calories == 250

    def test_negative_calories_raises_error(self):
        macros = Macros(protein=20, carbs=20, fat=10)
        with pytest.raises(ValueError, match="Calories cannot be negative"):
            Nutrition(calories=-100, macros=macros)
