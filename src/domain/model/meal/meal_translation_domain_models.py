"""
Meal translation domain models.

Stores translated content separately from original English to maintain
data integrity and support multiple languages.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class FoodItemTranslation:
    """
    Translated content for a single food item.

    Attributes:
        food_item_id: Reference to original food item
        name: Translated food name
        description: Optional translated description
    """
    food_item_id: str
    name: str
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "food_item_id": self.food_item_id,
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FoodItemTranslation":
        """Create from dictionary."""
        return cls(
            food_item_id=data["food_item_id"],
            name=data["name"],
            description=data.get("description"),
        )


@dataclass
class MealTranslation:
    """
    Translation of a meal to a specific language.

    Attributes:
        meal_id: Reference to original meal
        language: ISO 639-1 language code (e.g., 'vi', 'es')
        dish_name: Translated dish name
        food_items: List of translated food items
        translated_at: Timestamp of translation
    """
    meal_id: str
    language: str
    dish_name: str
    food_items: List[FoodItemTranslation]
    translated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "meal_id": self.meal_id,
            "language": self.language,
            "dish_name": self.dish_name,
            "food_items": [fi.to_dict() for fi in self.food_items],
            "translated_at": self.translated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MealTranslation":
        """Create from dictionary."""
        return cls(
            meal_id=data["meal_id"],
            language=data["language"],
            dish_name=data["dish_name"],
            food_items=[
                FoodItemTranslation.from_dict(fi) for fi in data["food_items"]
            ],
            translated_at=datetime.fromisoformat(data["translated_at"]),
        )

    def get_food_item_translation(self, food_item_id: str) -> Optional[FoodItemTranslation]:
        """Get translation for a specific food item."""
        for fi in self.food_items:
            if fi.food_item_id == food_item_id:
                return fi
        return None
