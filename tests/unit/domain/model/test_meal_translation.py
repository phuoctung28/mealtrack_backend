"""
Unit tests for meal translation domain models.
"""
import pytest
from datetime import datetime

from src.domain.model.meal import (
    MealTranslation,
    FoodItemTranslation,
)


class TestFoodItemTranslation:
    """Tests for FoodItemTranslation domain model."""

    def test_create_food_item_translation(self):
        """Test creating a food item translation."""
        translation = FoodItemTranslation(
            food_item_id="item-123",
            name="Gà nướng",
            description="Thịt gà được nướng với gia vị"
        )

        assert translation.food_item_id == "item-123"
        assert translation.name == "Gà nướng"
        assert translation.description == "Thịt gà được nướng với gia vị"

    def test_food_item_translation_to_dict(self):
        """Test serialization to dictionary."""
        translation = FoodItemTranslation(
            food_item_id="item-456",
            name="Bún bò",
            description=None
        )

        result = translation.to_dict()

        assert result["food_item_id"] == "item-456"
        assert result["name"] == "Bún bò"
        assert result["description"] is None

    def test_food_item_translation_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "food_item_id": "item-789",
            "name": "Phở",
            "description": "Bún phở truyền thống Việt Nam"
        }

        translation = FoodItemTranslation.from_dict(data)

        assert translation.food_item_id == "item-789"
        assert translation.name == "Phở"
        assert translation.description == "Bún phở truyền thống Việt Nam"


class TestMealTranslation:
    """Tests for MealTranslation domain model."""

    def test_create_meal_translation(self):
        """Test creating a meal translation."""
        food_items = [
            FoodItemTranslation(
                food_item_id="item-1",
                name="Gạo",
                description="Gạo trắng"
            ),
            FoodItemTranslation(
                food_item_id="item-2",
                name="Cá",
                description="Cá hồi"
            ),
        ]

        translation = MealTranslation(
            meal_id="meal-123",
            language="vi",
            dish_name="Cơm cá hồi",
            food_items=food_items
        )

        assert translation.meal_id == "meal-123"
        assert translation.language == "vi"
        assert translation.dish_name == "Cơm cá hồi"
        assert len(translation.food_items) == 2

    def test_meal_translation_to_dict(self):
        """Test serialization to dictionary."""
        food_items = [
            FoodItemTranslation(
                food_item_id="item-1",
                name="Chicken",
                description="Grilled chicken"
            ),
        ]

        translation = MealTranslation(
            meal_id="meal-456",
            language="es",
            dish_name="Pollo a la parrilla",
            food_items=food_items,
            translated_at=datetime(2026, 1, 28, 12, 0, 0)
        )

        result = translation.to_dict()

        assert result["meal_id"] == "meal-456"
        assert result["language"] == "es"
        assert result["dish_name"] == "Pollo a la parrilla"
        assert len(result["food_items"]) == 1
        assert result["food_items"][0]["name"] == "Chicken"

    def test_meal_translation_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "meal_id": "meal-789",
            "language": "zh",
            "dish_name": "炒饭",
            "food_items": [
                {
                    "food_item_id": "item-1",
                    "name": "米饭",
                    "description": "白米饭"
                }
            ],
            "translated_at": "2026-01-28T10:00:00"
        }

        translation = MealTranslation.from_dict(data)

        assert translation.meal_id == "meal-789"
        assert translation.language == "zh"
        assert translation.dish_name == "炒饭"
        assert len(translation.food_items) == 1
        assert translation.food_items[0].name == "米饭"

    def test_get_food_item_translation(self):
        """Test getting a specific food item translation."""
        food_items = [
            FoodItemTranslation(food_item_id="item-1", name="Rice"),
            FoodItemTranslation(food_item_id="item-2", name="Chicken"),
        ]

        translation = MealTranslation(
            meal_id="meal-001",
            language="vi",
            dish_name="Cơm gà",
            food_items=food_items
        )

        result = translation.get_food_item_translation("item-2")

        assert result is not None
        assert result.name == "Chicken"

    def test_get_food_item_translation_not_found(self):
        """Test getting a non-existent food item translation."""
        translation = MealTranslation(
            meal_id="meal-002",
            language="en",
            dish_name="Salad",
            food_items=[]
        )

        result = translation.get_food_item_translation("non-existent")

        assert result is None
