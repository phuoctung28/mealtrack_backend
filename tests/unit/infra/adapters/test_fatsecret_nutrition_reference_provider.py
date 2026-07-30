"""Tests for the FatSecret nutrition reference provider adapter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infra.adapters.fatsecret_nutrition_reference_provider import (
    FatSecretNutritionReferenceProvider,
)


@pytest.mark.asyncio
async def test_fatsecret_provider_delegates_staged_methods():
    fatsecret = MagicMock()
    fatsecret.search_food_candidates = AsyncMock(return_value=[{"food_id": "1"}])
    fatsecret.get_food_details = AsyncMock(return_value={"protein_100g": 10})
    provider = FatSecretNutritionReferenceProvider(fatsecret)

    candidates = await provider.search_food_candidates("rice", max_results=2)
    details = await provider.get_food_details("1")

    assert candidates == [{"food_id": "1"}]
    assert details == {"protein_100g": 10}
    fatsecret.search_food_candidates.assert_awaited_once_with(
        "rice",
        max_results=2,
        region="US",
        language="en",
    )
    fatsecret.get_food_details.assert_awaited_once_with(
        "1",
        region="US",
        language="en",
    )
