from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.app.services.catalog_meal_browse_ranking import (
    CatalogPopularityUnavailableError,
)
from src.app.services.catalog_meal_browse_service import (
    CatalogFeed,
    CatalogMealBrowseService,
)
from src.domain.model.meal_recommendation import CatalogMeal, CatalogMealIngredient
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
)
from src.domain.services.meal_recommendation.recipe_scoring_service import RecipeScore


def _meal(meal_id: str, *, rank: int | None, food_reference_id: int) -> CatalogMeal:
    return CatalogMeal(
        id=meal_id,
        catalog_key=meal_id,
        content_hash="a" * 64,
        name=meal_id.replace("-", " ").title(),
        cuisine="Japanese",
        description="description",
        image_url="https://example.test/meal.jpg",
        protein_g=Decimal("20"),
        carbs_g=Decimal("40"),
        fat_g=Decimal("10"),
        fiber_g=Decimal("2"),
        sugar_g=Decimal("1"),
        meal_types=("breakfast", "snack"),
        ingredients=(
            CatalogMealIngredient(
                food_reference_id=food_reference_id,
                display_name="Ingredient",
                quantity=Decimal("100"),
                unit="g",
            ),
        ),
        popularity_rank=rank,
    )


class _Uow:
    def __init__(self, meals):
        self.meals = SimpleNamespace(
            aggregate_linked_ingredient_history=self._aggregate_history
        )
        self.catalog_recipes = SimpleNamespace(get_meal=self._get_meal)
        self.meal_rows = meals
        self.writes = []

    async def _get_meal(self, catalog_id):
        return next((meal for meal in self.meal_rows if meal.id == catalog_id), None)

    async def _aggregate_history(self, **kwargs):
        return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class _UowFactory:
    def __init__(self, uow):
        self.uow = uow

    def __call__(self):
        return self.uow


class _Snapshot:
    def __init__(self, meals):
        self.snapshot = SimpleNamespace(
            meals=tuple(meals),
            ingredient_statistics=SimpleNamespace(idf=lambda _food_id: 1.0),
        )

    async def get_snapshot(self, _uow):
        return self.snapshot


class _History:
    def __init__(self):
        self.users = []

    async def build_affinity(self, _uow, *, user_id, start_date, timezone):
        self.users.append(user_id)
        food_reference_id = 1 if user_id == "user-a" else 2
        return IngredientAffinityProfile(
            weights={food_reference_id: 1.0},
            confidence=1.0,
        )


class _Scoring:
    def score(self, meal, *, affinity, **_kwargs):
        matched = meal.ingredients[0].food_reference_id in affinity.weights
        return RecipeScore(
            catalog_meal=meal,
            score=1.0 if matched else 0.0,
            calorie_fit=1.0 if matched else 0.0,
            ingredient_fit=1.0 if matched else 0.0,
        )


class _Diversity:
    def rerank_shortlist(self, ranked_pool, **_kwargs):
        return ranked_pool


def _service(meals, history=None):
    return CatalogMealBrowseService(
        uow_factory=_UowFactory(_Uow(meals)),
        snapshot_service=_Snapshot(meals),
        history_projector=history or _History(),
        scoring=_Scoring(),
        diversity=_Diversity(),
    )


@pytest.mark.asyncio
async def test_popular_feed_uses_curated_rank_then_stable_ties_and_paginates_after_ranking():
    meals = [
        _meal("meal-b", rank=2, food_reference_id=2),
        _meal("meal-a", rank=1, food_reference_id=1),
        _meal("meal-c", rank=2, food_reference_id=3),
    ]

    page = await _service(meals).list_meals(
        user_id="user-a",
        feed=CatalogFeed.POPULAR,
        limit=1,
        offset=1,
        query=None,
        cuisine=None,
        meal_type=None,
    )

    assert [meal.id for meal in page.items] == ["meal-b"]
    assert page.total == 3
    assert page.ranking_source == "curated"
    assert page.fallback is False


@pytest.mark.asyncio
async def test_for_you_uses_owner_scoped_history_without_persisting():
    meals = [
        _meal("meal-a", rank=1, food_reference_id=1),
        _meal("meal-b", rank=2, food_reference_id=2),
    ]
    history = _History()
    service = _service(meals, history)

    page_a = await service.list_meals(
        user_id="user-a",
        feed=CatalogFeed.FOR_YOU,
        limit=20,
        offset=0,
        query=None,
        cuisine=None,
        meal_type="breakfast",
        daily_calories=2000,
        start_date=date(2026, 8, 16),
        timezone="UTC",
    )
    page_b = await service.list_meals(
        user_id="user-b",
        feed=CatalogFeed.FOR_YOU,
        limit=20,
        offset=0,
        query=None,
        cuisine=None,
        meal_type="breakfast",
        daily_calories=2000,
        start_date=date(2026, 8, 16),
        timezone="UTC",
    )

    assert [meal.id for meal in page_a.items] == ["meal-a", "meal-b"]
    assert [meal.id for meal in page_b.items] == ["meal-b", "meal-a"]
    assert history.users == ["user-a", "user-b"]


@pytest.mark.asyncio
async def test_missing_popularity_source_fails_closed():
    with pytest.raises(CatalogPopularityUnavailableError):
        await _service([_meal("meal-a", rank=None, food_reference_id=1)]).list_meals(
            user_id="user-a",
            feed=CatalogFeed.POPULAR,
            limit=20,
            offset=0,
            query=None,
            cuisine=None,
            meal_type=None,
        )


@pytest.mark.asyncio
async def test_partial_popularity_source_fails_closed():
    with pytest.raises(CatalogPopularityUnavailableError):
        await _service(
            [
                _meal("meal-a", rank=1, food_reference_id=1),
                _meal("meal-b", rank=None, food_reference_id=2),
            ]
        ).list_meals(
            user_id="user-a",
            feed=CatalogFeed.POPULAR,
            limit=20,
            offset=0,
            query=None,
            cuisine=None,
            meal_type=None,
        )


@pytest.mark.asyncio
async def test_cold_start_for_you_falls_back_to_popular():
    class _EmptyHistory(_History):
        async def build_affinity(self, *_args, **_kwargs):
            return IngredientAffinityProfile(weights={}, confidence=0.0)

    page = await _service(
        [_meal("meal-a", rank=1, food_reference_id=1)], _EmptyHistory()
    ).list_meals(
        user_id="user-a",
        feed=CatalogFeed.FOR_YOU,
        limit=20,
        offset=0,
        query=None,
        cuisine=None,
        meal_type=None,
        daily_calories=2000,
        start_date=date(2026, 8, 16),
        timezone="UTC",
    )

    assert page.fallback is True
    assert page.ranking_source == "curated"
    assert [meal.id for meal in page.items] == ["meal-a"]


@pytest.mark.asyncio
async def test_get_meal_loads_one_row_without_snapshot():
    meals = [_meal("meal-a", rank=1, food_reference_id=1)]
    snapshot = _Snapshot(meals)
    service = CatalogMealBrowseService(
        uow_factory=_UowFactory(_Uow(meals)),
        snapshot_service=snapshot,
        history_projector=_History(),
        scoring=_Scoring(),
        diversity=_Diversity(),
    )
    snapshot.get_snapshot = None  # would fail if browse snapshot path is used

    meal = await service.get_meal("meal-a")

    assert meal.id == "meal-a"
    with pytest.raises(KeyError):
        await service.get_meal("missing")
