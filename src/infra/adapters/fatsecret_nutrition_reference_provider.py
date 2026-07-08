"""Nutrition reference provider backed by FatSecret."""

from typing import Any

from src.infra.adapters.fat_secret_service import FatSecretService


class FatSecretNutritionReferenceProvider:
    """Adapter exposing staged FatSecret lookups through a small port."""

    def __init__(self, fatsecret_service: FatSecretService):
        self._fatsecret_service = fatsecret_service

    async def search_food_candidates(
        self,
        query: str,
        max_results: int = 5,
        region: str = "US",
        language: str = "en",
    ) -> list[dict[str, Any]]:
        return await self._fatsecret_service.search_food_candidates(
            query,
            max_results=max_results,
            region=region,
            language=language,
        )

    async def get_food_details(
        self,
        food_id: str,
        region: str = "US",
        language: str = "en",
    ) -> dict[str, Any] | None:
        return await self._fatsecret_service.get_food_details(
            food_id,
            region=region,
            language=language,
        )
