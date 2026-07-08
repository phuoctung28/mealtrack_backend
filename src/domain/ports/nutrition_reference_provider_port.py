"""Port for optional nutrition reference providers."""

from typing import Any, Protocol


class NutritionReferenceProviderPort(Protocol):
    """Provider interface for staged nutrition reference lookup."""

    async def search_food_candidates(
        self,
        query: str,
        max_results: int = 5,
        region: str = "US",
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """Return candidates without fetching every detail payload."""

    async def get_food_details(
        self,
        food_id: str,
        region: str = "US",
        language: str = "en",
    ) -> dict[str, Any] | None:
        """Return detailed nutrition for one selected candidate."""
