"""
Unit tests for IngredientNutritionResolver.

All FatSecret interactions are mocked — no real API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.services.meal_suggestion.ingredient_nutrition_resolver import (
    IngredientNutritionResolver,
    PerHundredGramsMacros,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_generic_result(
    food_id: str = "fs-1",
    food_type: str = "Generic",
    protein: float = 23.1,
    carbs: float = 0.0,
    fat: float = 2.6,
) -> dict:
    """Build a minimal FatSecret search result dict."""
    return {
        "food_id": food_id,
        "description": "Chicken Breast",
        "food_type": food_type,
        "source": "fatsecret",
        "protein_100g": protein,
        "carbs_100g": carbs,
        "fat_100g": fat,
    }


def _make_branded_result(food_id: str = "fs-99") -> dict:
    return _make_generic_result(
        food_id=food_id,
        food_type="Brand",
        protein=20.0,
        carbs=5.0,
        fat=3.0,
    )


@pytest.fixture
def mock_fatsecret():
    """Mock FatSecretService with async search_foods."""
    svc = MagicMock()
    svc.search_foods = AsyncMock()
    return svc


@pytest.fixture
def mock_repo():
    """Mock FoodReferenceRepository — upsert_by_normalized_name is sync."""
    repo = MagicMock()
    repo.upsert_by_normalized_name = MagicMock(return_value={"id": 1})
    return repo


@pytest.fixture
def resolver(mock_fatsecret, mock_repo):
    return IngredientNutritionResolver(
        fatsecret=mock_fatsecret,
        food_ref_repo=mock_repo,
    )


# ---------------------------------------------------------------------------
# resolve() — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_chicken_breast_returns_macros(
    resolver, mock_fatsecret, mock_repo
):
    """resolve('chicken breast') with mocked generic result returns PerHundredGramsMacros."""
    mock_fatsecret.search_foods.return_value = [_make_generic_result()]

    result = await resolver.resolve("chicken breast")

    assert result is not None
    assert isinstance(result, PerHundredGramsMacros)
    assert result.protein == pytest.approx(23.1)
    assert result.carbs == pytest.approx(0.0)
    assert result.fat == pytest.approx(2.6)
    assert result.fiber == pytest.approx(0.0)
    assert result.sugar == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_resolve_calls_upsert_on_hit(resolver, mock_fatsecret, mock_repo):
    """Successful resolve upserts to food_reference."""
    mock_fatsecret.search_foods.return_value = [_make_generic_result()]

    await resolver.resolve("chicken breast")

    mock_repo.upsert_by_normalized_name.assert_called_once()
    call_kwargs = mock_repo.upsert_by_normalized_name.call_args.kwargs
    assert call_kwargs["source"] == "fatsecret"
    assert call_kwargs["is_verified"] is False
    assert call_kwargs["protein_100g"] == pytest.approx(23.1)


@pytest.mark.asyncio
async def test_resolve_passes_normalized_name_to_upsert(
    resolver, mock_fatsecret, mock_repo
):
    """name_normalized passed to upsert is the normalize_food_name() output."""
    mock_fatsecret.search_foods.return_value = [_make_generic_result()]

    await resolver.resolve("Raw Chicken Breast")

    call_kwargs = mock_repo.upsert_by_normalized_name.call_args.kwargs
    # "raw" qualifier removed by normalize_food_name
    assert "raw" not in call_kwargs["name_normalized"]
    assert "chicken" in call_kwargs["name_normalized"]


# ---------------------------------------------------------------------------
# resolve() — empty / no results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_returns_none_on_empty_results(
    resolver, mock_fatsecret, mock_repo
):
    """resolve() returns None when FatSecret finds nothing."""
    mock_fatsecret.search_foods.return_value = []

    result = await resolver.resolve("exotic_unknown_food_xyzzy")

    assert result is None
    mock_repo.upsert_by_normalized_name.assert_not_called()


# ---------------------------------------------------------------------------
# resolve() — rate limit / network exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_returns_none_on_fatsecret_exception(
    resolver, mock_fatsecret, mock_repo
):
    """FatSecret exception (network/rate-limit) returns None gracefully."""
    mock_fatsecret.search_foods.side_effect = Exception("429 Too Many Requests")

    result = await resolver.resolve("chicken breast")

    assert result is None
    mock_repo.upsert_by_normalized_name.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_logs_warning_on_fatsecret_exception(
    resolver, mock_fatsecret, mock_repo, caplog
):
    """A warning is logged when FatSecret raises an exception."""
    import logging

    mock_fatsecret.search_foods.side_effect = Exception("429 Too Many Requests")

    with caplog.at_level(logging.WARNING):
        await resolver.resolve("chicken breast")

    assert any("chicken breast" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# resolve() — missing macro fields in FatSecret result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_returns_none_when_macros_missing(
    resolver, mock_fatsecret, mock_repo
):
    """If FatSecret result is missing required macro fields, returns None."""
    incomplete = {
        "food_id": "fs-2",
        "food_type": "Generic",
        "description": "Mystery food",
    }
    mock_fatsecret.search_foods.return_value = [incomplete]

    result = await resolver.resolve("mystery food")

    assert result is None
    mock_repo.upsert_by_normalized_name.assert_not_called()


# ---------------------------------------------------------------------------
# _pick_generic()
# ---------------------------------------------------------------------------


class TestPickGeneric:
    """Unit tests for the generic-preference filter."""

    def test_prefers_generic_over_branded(self):
        branded = _make_branded_result(food_id="fs-99")
        generic = _make_generic_result(food_id="fs-1")
        results = [branded, generic]

        chosen = IngredientNutritionResolver._pick_generic(results)

        assert chosen["food_id"] == "fs-1"
        assert chosen["food_type"] == "Generic"

    def test_falls_back_to_first_result_when_no_generic(self):
        branded_a = _make_branded_result(food_id="fs-10")
        branded_b = _make_branded_result(food_id="fs-11")
        results = [branded_a, branded_b]

        chosen = IngredientNutritionResolver._pick_generic(results)

        assert chosen["food_id"] == "fs-10"

    def test_returns_none_for_empty_list(self):
        assert IngredientNutritionResolver._pick_generic([]) is None

    def test_returns_generic_even_when_it_is_last(self):
        results = [
            _make_branded_result("fs-1"),
            _make_branded_result("fs-2"),
            _make_branded_result("fs-3"),
            _make_generic_result("fs-4"),
        ]
        chosen = IngredientNutritionResolver._pick_generic(results)
        assert chosen["food_id"] == "fs-4"

    def test_generic_food_type_case_insensitive(self):
        result = _make_generic_result(food_type="GENERIC")
        chosen = IngredientNutritionResolver._pick_generic([result])
        assert chosen is result

    def test_single_result_always_returned(self):
        only = _make_branded_result("fs-only")
        assert IngredientNutritionResolver._pick_generic([only]) is only


# ---------------------------------------------------------------------------
# upsert failure is non-fatal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_returns_macros_even_if_upsert_fails(
    resolver, mock_fatsecret, mock_repo
):
    """Cache warm-up failures must not propagate — macros are still returned."""
    mock_fatsecret.search_foods.return_value = [_make_generic_result()]
    mock_repo.upsert_by_normalized_name.side_effect = Exception("DB connection lost")

    result = await resolver.resolve("chicken breast")

    # Macros should still be returned despite upsert failure
    assert result is not None
    assert result.protein == pytest.approx(23.1)
