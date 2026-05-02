"""
Port for recipe search services following clean architecture.
Enables semantic search for recipes without depending on specific implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RecipeSearchCriteria:
    """Search criteria for recipe lookup."""

    meal_type: str
    target_calories: int
    calorie_tolerance: int = 100  # ±100 cal
    max_cook_time: int | None = None
    dietary_preferences: list[str] | None = None
    allergies: list[str] | None = None
    ingredients: list[str] | None = None
    exclude_ids: list[str] | None = None

    def __post_init__(self):
        """Initialize default values for list fields."""
        if self.dietary_preferences is None:
            self.dietary_preferences = []
        if self.allergies is None:
            self.allergies = []
        if self.ingredients is None:
            self.ingredients = []
        if self.exclude_ids is None:
            self.exclude_ids = []


@dataclass
class RecipeSearchResult:
    """Result from recipe search."""

    recipe_id: str
    name: str
    calories: int
    cook_time: int
    ingredients: list[str]
    instructions: list[str]
    score: float  # Relevance score


class RecipeSearchPort(ABC):
    """Port for recipe search operations."""

    @abstractmethod
    def search_recipes(
        self, criteria: RecipeSearchCriteria, limit: int = 5
    ) -> list[RecipeSearchResult]:
        """
        Search for recipes matching the criteria.

        Args:
            criteria: Search criteria
            limit: Maximum number of results

        Returns:
            List of matching recipes
        """
        pass

    @abstractmethod
    def get_recipe_by_id(self, recipe_id: str) -> RecipeSearchResult | None:
        """
        Get a specific recipe by ID.

        Args:
            recipe_id: The recipe ID

        Returns:
            Recipe if found, None otherwise
        """
        pass
