from datetime import date
from decimal import Decimal

import pytest

from src.app.services.recommended_meal_materialization_service import (
    RecommendedMealMaterializationService,
)
from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationNotFoundError,
)
from src.domain.model.meal_recommendation import (
    CatalogMeal,
    CatalogMealIngredient,
    PersistedMealRecommendationCandidate,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)


class _CatalogRepo:
    async def get_meal(self, catalog_meal_id):
        return CatalogMeal(
            id=catalog_meal_id,
            catalog_key="catalog-key",
            content_hash="a" * 64,
            name="Catalog Recipe",
            cuisine="vietnamese",
            description=None,
            image_url=None,
            protein_g=Decimal("30"),
            carbs_g=Decimal("50"),
            fat_g=Decimal("10"),
            fiber_g=Decimal("5"),
            meal_types=("breakfast",),
            ingredients=(
                CatalogMealIngredient(
                    food_reference_id=123,
                    display_name="Ingredient",
                    quantity=Decimal("100"),
                    unit="g",
                ),
            ),
        )


class _MissingCatalogRepo:
    async def get_meal(self, catalog_meal_id):
        return None


class _MealRepo:
    def __init__(self):
        self.saved = None

    async def save(self, meal):
        self.saved = meal
        return meal


class _Uow:
    def __init__(self, catalog_recipes=None):
        self.catalog_recipes = catalog_recipes or _CatalogRepo()
        self.meals = _MealRepo()


def _plan_and_slot():
    plan = PersistedMealRecommendationPlan(
        id="plan-1",
        user_id="00000000-0000-0000-0000-000000000001",
        status="active",
        timezone="UTC",
        start_date=date(2026, 7, 16),
        daily_calories=2000,
        algorithm_version="catalog_deterministic_v1",
        operation="three_day",
        idempotency_key="key",
        request_fingerprint="f" * 64,
    )
    catalog_meal = CatalogMeal(
        id="catalog-1",
        catalog_key="catalog-key",
        content_hash="a" * 64,
        name="Catalog Recipe",
        cuisine="vietnamese",
        description=None,
        image_url=None,
        protein_g=Decimal("30"),
        carbs_g=Decimal("50"),
        fat_g=Decimal("10"),
        fiber_g=Decimal("5"),
        meal_types=("breakfast",),
        ingredients=(
            CatalogMealIngredient(
                food_reference_id=123,
                display_name="Ingredient",
                quantity=Decimal("100"),
                unit="g",
            ),
        ),
    )
    slot = PersistedMealRecommendationSlot(
        id="slot-1",
        slot_date=date(2026, 7, 16),
        day_index=0,
        meal_type="breakfast",
        catalog_meal_id="catalog-1",
        target_calories=500,
        score=1.0,
        position=0,
        selected=PersistedMealRecommendationCandidate(
            id="candidate-1",
            slot_id="slot-1",
            recommendation_date=date(2026, 7, 16),
            meal_type="breakfast",
            catalog_meal_id="catalog-1",
            candidate_rank=0,
            is_selected=True,
            score=Decimal("1.0"),
            selection_version=1,
            catalog_meal=catalog_meal,
        ),
    )
    return plan, slot


@pytest.mark.asyncio
async def test_materializer_preserves_food_reference_ids_and_macro_snapshot():
    plan, slot = _plan_and_slot()

    meal = await RecommendedMealMaterializationService().materialize(
        _Uow(),
        plan=plan,
        slot=slot,
    )

    assert meal.source == "meal_recommendation"
    assert meal.nutrition is not None
    assert meal.nutrition.macros.protein == 30
    assert meal.nutrition.food_items[0].food_reference_id == 123
    assert meal.image is None


@pytest.mark.asyncio
async def test_materializer_fails_with_public_error_when_selected_meal_missing():
    plan, slot = _plan_and_slot()
    slot = PersistedMealRecommendationSlot(
        **{**slot.__dict__, "selected": None}
    )

    with pytest.raises(MealRecommendationNotFoundError):
        await RecommendedMealMaterializationService().materialize(
            _Uow(),
            plan=plan,
            slot=slot,
        )
