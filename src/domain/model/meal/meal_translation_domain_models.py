"""
Meal translation domain models.

Stores translated content separately from original English to maintain
data integrity and support multiple languages.
"""

from dataclasses import dataclass, field
from datetime import datetime

CURRENT_MEAL_TRANSLATION_VERSION = 2


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
    description: str | None = None

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
        food_items: List of translated food items (legacy – kept for backward compat)
        translated_at: Timestamp of translation
        meal_instruction: Translated instructions as List[{instruction, duration_minutes}]
        meal_ingredients: Translated ingredient names as List[str] (same order as food items)
        translation_version: Contract version used to create the persisted row.
    """

    meal_id: str
    language: str
    dish_name: str
    food_items: list[FoodItemTranslation]
    translated_at: datetime = field(default_factory=datetime.utcnow)
    meal_instruction: list | None = None
    meal_ingredients: list | None = None
    translation_version: int | None = CURRENT_MEAL_TRANSLATION_VERSION

    def is_fully_cached(
        self,
        *,
        expected_ingredient_count: int | None = None,
        expected_instruction_count: int | None = None,
        expected_translation_version: int = CURRENT_MEAL_TRANSLATION_VERSION,
    ) -> bool:
        """Return whether the row covers the available source manifest."""
        if (
            self.translation_version != expected_translation_version
            or self.dish_name is None
            or self.meal_ingredients is None
        ):
            return False
        if (
            expected_ingredient_count is not None
            and len(self.meal_ingredients) != expected_ingredient_count
        ):
            return False
        if expected_instruction_count is None:
            return self.meal_instruction is not None
        if expected_instruction_count == 0:
            return self.meal_instruction in (None, [])
        return (
            self.meal_instruction is not None
            and len(self.meal_instruction) == expected_instruction_count
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "meal_id": self.meal_id,
            "language": self.language,
            "dish_name": self.dish_name,
            "food_items": [fi.to_dict() for fi in self.food_items],
            "translated_at": self.translated_at.isoformat(),
            "translation_version": self.translation_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MealTranslation":
        """Create from dictionary."""
        return cls(
            meal_id=data["meal_id"],
            language=data["language"],
            dish_name=data["dish_name"],
            food_items=[FoodItemTranslation.from_dict(fi) for fi in data["food_items"]],
            translated_at=datetime.fromisoformat(data["translated_at"]),
            translation_version=data.get(
                "translation_version", CURRENT_MEAL_TRANSLATION_VERSION
            ),
        )

    def get_food_item_translation(
        self, food_item_id: str
    ) -> FoodItemTranslation | None:
        """Get translation for a specific food item."""
        for fi in self.food_items:
            if fi.food_item_id == food_item_id:
                return fi
        return None
