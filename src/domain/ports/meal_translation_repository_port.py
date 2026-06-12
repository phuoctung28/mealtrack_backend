"""
Meal translation repository port interface.
"""

from abc import ABC, abstractmethod

from src.domain.model.meal import MealTranslation


class MealTranslationRepositoryPort(ABC):
    """Port interface for meal translation persistence operations."""

    @abstractmethod
    async def save(self, translation: MealTranslation) -> MealTranslation:
        """
        Persist a meal translation.

        Args:
            translation: The translation to save

        Returns:
            The saved translation with generated IDs
        """
        pass

    @abstractmethod
    async def get_by_meal_and_language(
        self, meal_id: str, language: str
    ) -> MealTranslation | None:
        """
        Get translation for a specific meal and language.

        Args:
            meal_id: The meal ID
            language: ISO 639-1 language code

        Returns:
            The translation if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_by_meal(self, meal_id: str) -> int:
        """
        Delete all translations for a meal.

        Args:
            meal_id: The meal ID

        Returns:
            Number of translations deleted
        """
        pass
