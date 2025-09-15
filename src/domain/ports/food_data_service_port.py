from abc import ABC, abstractmethod
from typing import Any, Dict, List


class FoodDataServicePort(ABC):
    """
    Port interface for external food data providers (e.g., USDA FoodData Central).

    Responsible for network-bound lookups of food search results and detailed
    nutrition data, returning provider-native payloads for a separate mapping layer
    to transform.
    """

    @abstractmethod
    async def search_foods(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search foods by a free-text query.

        Args:
            query: Search terms entered by the user (e.g., "chicken breast").
            limit: Maximum number of results to return (default: 20).

        Returns:
            A list of provider-native search result dictionaries.

        Raises:
            Exception: If the provider returns an error or the request fails.
        """
        pass

    @abstractmethod
    async def get_food_details(self, fdc_id: int) -> Dict[str, Any]:
        """
        Get detailed nutrient information for a single food item.

        Args:
            fdc_id: Provider food identifier (USDA FDC ID).

        Returns:
            A provider-native details dictionary including nutrients and portions.

        Raises:
            Exception: If the provider returns an error or the request fails.
        """
        pass

    @abstractmethod
    async def get_multiple_foods(self, fdc_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Batch fetch multiple foods by their provider IDs.

        Args:
            fdc_ids: List of provider food identifiers (FDC IDs).

        Returns:
            A list of provider-native details dictionaries, one per ID.

        Raises:
            Exception: If the provider returns an error or the request fails.
        """
        pass
