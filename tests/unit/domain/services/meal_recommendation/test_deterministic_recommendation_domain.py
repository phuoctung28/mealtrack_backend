from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.domain.model.meal_recommendation import (
    CatalogMeal,
    CatalogMealIngredient,
    MealRecommendationInsufficiency,
    MealRecommendationInsufficiencyReason,
)
from src.domain.services.meal_recommendation.calorie_allocation_policy import (
    CalorieAllocationPolicy,
)
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityService,
    IngredientHistoryEvent,
)
from src.domain.services.meal_recommendation.recipe_scoring_service import (
    RecipeScoringService,
)
from src.domain.services.meal_recommendation.three_day_plan_optimizer import (
    ALGORITHM_VERSION,
    ThreeDayPlanOptimizer,
)


def _catalog_meal(
    catalog_meal_id: str,
    meal_type: str,
    calories: int,
    *,
    cuisine: str = "vietnamese",
    food_reference_id: int = 1,
    status: str = "published",
) -> CatalogMeal:
    return CatalogMeal(
        id=catalog_meal_id,
        catalog_key=f"key-{catalog_meal_id}",
        content_hash=f"{catalog_meal_id:0<64}"[:64],
        name=f"Recipe {catalog_meal_id}",
        cuisine=cuisine,
        description=None,
        image_url=None,
        protein_g=Decimal(str(calories / 4)),
        carbs_g=Decimal("0"),
        fat_g=Decimal("0"),
        fiber_g=Decimal("0"),
        meal_types=(meal_type,),
        ingredients=(
            CatalogMealIngredient(
                food_reference_id=food_reference_id,
                display_name="Ingredient",
                quantity=Decimal("100"),
                unit="g",
            ),
        ),
        is_active=status == "published",
    )


def _candidate_pool() -> list[CatalogMeal]:
    catalog_meals = []
    calorie_targets = {
        "breakfast": 500,
        "lunch": 750,
        "dinner": 750,
    }
    for meal_type, target in calorie_targets.items():
        for index in range(9):
            catalog_meals.append(
                _catalog_meal(
                    catalog_meal_id=f"{meal_type}-{index:02d}",
                    meal_type=meal_type,
                    calories=target + index,
                    food_reference_id=index + 1,
                )
            )
    return catalog_meals


def test_calorie_allocation_is_deterministic_and_balanced():
    allocation = CalorieAllocationPolicy().allocate(2000)

    assert allocation == {"breakfast": 500, "lunch": 750, "dinner": 750}
    assert sum(allocation.values()) == 2000


def test_ingredient_affinity_uses_only_recent_linked_history():
    now = datetime(2026, 7, 16, tzinfo=UTC)
    service = IngredientAffinityService()

    profile = service.build_profile(
        [
            IngredientHistoryEvent(7, now - timedelta(days=1), 200),
            IngredientHistoryEvent(8, now - timedelta(days=120), 500),
            IngredientHistoryEvent(0, now, 500),
        ],
        now=now,
    )

    assert set(profile.weights) == {7}
    assert profile.weights[7] == pytest.approx(1.0)
    assert profile.confidence > 0


def test_ingredient_affinity_accepts_naive_now_with_aware_events():
    aware_event_time = datetime(2026, 7, 16, tzinfo=UTC)
    naive_now = datetime(2026, 7, 17)

    profile = IngredientAffinityService().build_profile(
        [IngredientHistoryEvent(7, aware_event_time, 100)],
        now=naive_now,
    )

    assert profile.weights[7] == pytest.approx(1.0)


def test_scoring_stable_tie_breaks_by_catalog_meal_version_id():
    catalog_meals = [
        _catalog_meal("b-version", "breakfast", 500),
        _catalog_meal("a-version", "breakfast", 500),
    ]
    ranked = RecipeScoringService().rank(
        catalog_meals,
        meal_type="breakfast",
        target_calories=500,
        affinity=IngredientAffinityService().build_profile([], now=datetime.now(UTC)),
    )

    assert [item.catalog_meal.id for item in ranked] == ["a-version", "b-version"]
    assert ranked[0].score == ranked[1].score


def test_scoring_stays_within_bounds():
    profile = IngredientAffinityService().build_profile(
        [IngredientHistoryEvent(1, datetime.now(UTC), 100)],
        now=datetime.now(UTC),
    )

    score = RecipeScoringService().score(
        _catalog_meal("candidate", "breakfast", 500, food_reference_id=1),
        target_calories=500,
        affinity=profile,
    )

    assert 0 <= score.score <= 1


def test_optimizer_fallback_is_distance_ranked_after_tolerance_misses():
    affinity = IngredientAffinityService().build_profile(
        [IngredientHistoryEvent(99, datetime.now(UTC), 500)],
        now=datetime.now(UTC),
    )
    optimizer = ThreeDayPlanOptimizer()
    catalog_meals = [
        _catalog_meal("far-affinity", "breakfast", 1200, food_reference_id=99),
        _catalog_meal("closer-no-affinity", "breakfast", 900, food_reference_id=1),
    ]

    ranked = optimizer._rank_with_fallback(
        catalog_meals,
        meal_type="breakfast",
        target_calories=500,
        affinity=affinity,
        selected_ids=set(),
    )

    assert [item.catalog_meal.id for item in ranked] == [
        "closer-no-affinity",
        "far-affinity",
    ]


def test_three_day_optimizer_produces_9_slots_and_45_alternatives():
    profile = IngredientAffinityService().build_profile([], now=datetime.now(UTC))

    result = ThreeDayPlanOptimizer().build_plan(
        _candidate_pool(),
        daily_calories=2000,
        affinity=profile,
        cuisines={"vietnamese"},
    )

    assert not isinstance(result, MealRecommendationInsufficiency)
    assert result.algorithm_version == ALGORITHM_VERSION
    assert len(result.slots) == 9
    assert len({slot.catalog_meal.id for slot in result.slots}) == 9
    assert set(result.alternatives) == {
        (day_index, meal_type)
        for day_index in range(3)
        for meal_type in ("breakfast", "lunch", "dinner")
    }
    assert sum(len(items) for items in result.alternatives.values()) == 45
    for slot in result.slots:
        alternatives = result.alternatives[(slot.day_index, slot.meal_type)]
        assert len({item.catalog_meal.id for item in alternatives}) == 5
        assert slot.catalog_meal.id not in {item.catalog_meal.id for item in alternatives}


def test_three_day_optimizer_matches_normal_golden_ids_and_scores():
    profile = IngredientAffinityService().build_profile(
        [], now=datetime(2026, 7, 16, tzinfo=UTC)
    )

    result = ThreeDayPlanOptimizer().build_plan(
        _candidate_pool(),
        daily_calories=2000,
        affinity=profile,
        cuisines={"vietnamese"},
    )

    assert not isinstance(result, MealRecommendationInsufficiency)
    assert [
        (slot.day_index, slot.meal_type, slot.catalog_meal.id, round(slot.score, 6))
        for slot in result.slots
    ] == [
        (0, "breakfast", "breakfast-00", 0.82),
        (0, "lunch", "lunch-00", 0.82),
        (0, "dinner", "dinner-00", 0.82),
        (1, "breakfast", "breakfast-01", 0.81836),
        (1, "lunch", "lunch-01", 0.818907),
        (1, "dinner", "dinner-01", 0.818907),
        (2, "breakfast", "breakfast-02", 0.81672),
        (2, "lunch", "lunch-02", 0.817813),
        (2, "dinner", "dinner-02", 0.817813),
    ]
    assert {
        key: [(item.catalog_meal.id, round(item.score, 6)) for item in alternatives]
        for key, alternatives in result.alternatives.items()
    } == _expected_normal_alternatives()


def test_three_day_optimizer_matches_affinity_golden_ids_and_scores():
    profile = IngredientAffinityService().build_profile(
        [IngredientHistoryEvent(3, datetime(2026, 7, 15, tzinfo=UTC), 250)],
        now=datetime(2026, 7, 16, tzinfo=UTC),
    )

    result = ThreeDayPlanOptimizer().build_plan(
        _candidate_pool(),
        daily_calories=2000,
        affinity=profile,
        cuisines={"vietnamese"},
    )

    assert not isinstance(result, MealRecommendationInsufficiency)
    assert [
        (slot.day_index, slot.meal_type, slot.catalog_meal.id, round(slot.score, 6))
        for slot in result.slots
    ] == [
        (0, "breakfast", "breakfast-02", 0.83452),
        (0, "lunch", "lunch-02", 0.835613),
        (0, "dinner", "dinner-02", 0.835613),
        (1, "breakfast", "breakfast-00", 0.82),
        (1, "lunch", "lunch-00", 0.82),
        (1, "dinner", "dinner-00", 0.82),
        (2, "breakfast", "breakfast-01", 0.81836),
        (2, "lunch", "lunch-01", 0.818907),
        (2, "dinner", "dinner-01", 0.818907),
    ]
    assert {
        key: [(item.catalog_meal.id, round(item.score, 6)) for item in alternatives]
        for key, alternatives in result.alternatives.items()
    } == _expected_normal_alternatives()


def test_three_day_optimizer_returns_typed_insufficiency_for_sparse_catalog():
    profile = IngredientAffinityService().build_profile([], now=datetime.now(UTC))

    result = ThreeDayPlanOptimizer().build_plan(
        [_catalog_meal("breakfast-only", "breakfast", 500)],
        daily_calories=2000,
        affinity=profile,
    )

    assert isinstance(result, MealRecommendationInsufficiency)
    assert result.reason == MealRecommendationInsufficiencyReason.NOT_ENOUGH_CURRENT_RECIPES


def test_optimizer_is_repeatable_for_same_inputs():
    profile = IngredientAffinityService().build_profile([], now=datetime.now(UTC))
    optimizer = ThreeDayPlanOptimizer()
    catalog_meals = _candidate_pool()

    first = optimizer.build_plan(catalog_meals, daily_calories=2000, affinity=profile)
    second = optimizer.build_plan(list(reversed(catalog_meals)), daily_calories=2000, affinity=profile)

    assert not isinstance(first, MealRecommendationInsufficiency)
    assert not isinstance(second, MealRecommendationInsufficiency)
    assert _slot_golden(first) == _slot_golden(second)
    assert _alternative_golden(first) == _alternative_golden(second)


def _slot_golden(plan):
    return [
        (slot.day_index, slot.meal_type, slot.catalog_meal.id, round(slot.score, 6))
        for slot in plan.slots
    ]


def _alternative_golden(plan):
    return {
        key: [(item.catalog_meal.id, round(item.score, 6)) for item in alternatives]
        for key, alternatives in plan.alternatives.items()
    }


def _expected_normal_alternatives():
    breakfast = [
        ("breakfast-03", 0.81508),
        ("breakfast-04", 0.81344),
        ("breakfast-05", 0.8118),
        ("breakfast-06", 0.81016),
        ("breakfast-07", 0.80852),
    ]
    lunch = [
        ("lunch-03", 0.81672),
        ("lunch-04", 0.815627),
        ("lunch-05", 0.814533),
        ("lunch-06", 0.81344),
        ("lunch-07", 0.812347),
    ]
    dinner = [
        ("dinner-03", 0.81672),
        ("dinner-04", 0.815627),
        ("dinner-05", 0.814533),
        ("dinner-06", 0.81344),
        ("dinner-07", 0.812347),
    ]
    return {
        (day_index, "breakfast"): breakfast
        for day_index in range(3)
    } | {
        (day_index, "lunch"): lunch
        for day_index in range(3)
    } | {
        (day_index, "dinner"): dinner
        for day_index in range(3)
    }
