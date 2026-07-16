from datetime import UTC, datetime, timedelta

import pytest

from src.domain.model.meal_recommendation import (
    CatalogRecipeIngredient,
    CatalogRecipeVersion,
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


def _recipe(
    recipe_id: str,
    meal_type: str,
    calories: int,
    *,
    cuisine: str = "vietnamese",
    food_reference_id: int = 1,
    status: str = "published",
) -> CatalogRecipeVersion:
    return CatalogRecipeVersion(
        id=recipe_id,
        recipe_id=f"recipe-{recipe_id}",
        release_id="release-1",
        recipe_key=f"key-{recipe_id}",
        name=f"Recipe {recipe_id}",
        cuisine=cuisine,
        status=status,
        version_number=1,
        calories=calories,
        protein_g=20,
        carbs_g=35,
        fat_g=12,
        fiber_g=4,
        meal_types=(meal_type,),
        ingredients=(
            CatalogRecipeIngredient(
                food_reference_id=food_reference_id,
                name="Ingredient",
                quantity=100,
                unit="g",
                resolved_grams=100,
                protein_g=10,
                carbs_g=10,
                fat_g=5,
            ),
        ),
    )


def _candidate_pool() -> list[CatalogRecipeVersion]:
    recipes = []
    calorie_targets = {
        "breakfast": 500,
        "lunch": 750,
        "dinner": 750,
    }
    for meal_type, target in calorie_targets.items():
        for index in range(9):
            recipes.append(
                _recipe(
                    recipe_id=f"{meal_type}-{index:02d}",
                    meal_type=meal_type,
                    calories=target + index,
                    food_reference_id=index + 1,
                )
            )
    return recipes


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


def test_scoring_stable_tie_breaks_by_recipe_version_id():
    recipes = [
        _recipe("b-version", "breakfast", 500),
        _recipe("a-version", "breakfast", 500),
    ]
    ranked = RecipeScoringService().rank(
        recipes,
        meal_type="breakfast",
        target_calories=500,
        affinity=IngredientAffinityService().build_profile([], now=datetime.now(UTC)),
    )

    assert [item.recipe.id for item in ranked] == ["a-version", "b-version"]
    assert ranked[0].score == ranked[1].score


def test_scoring_stays_within_bounds():
    profile = IngredientAffinityService().build_profile(
        [IngredientHistoryEvent(1, datetime.now(UTC), 100)],
        now=datetime.now(UTC),
    )

    score = RecipeScoringService().score(
        _recipe("candidate", "breakfast", 500, food_reference_id=1),
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
    recipes = [
        _recipe("far-affinity", "breakfast", 1200, food_reference_id=99),
        _recipe("closer-no-affinity", "breakfast", 900, food_reference_id=1),
    ]

    ranked = optimizer._rank_with_fallback(
        recipes,
        meal_type="breakfast",
        target_calories=500,
        affinity=affinity,
        selected_ids=set(),
    )

    assert [item.recipe.id for item in ranked] == [
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
    assert len({slot.recipe.id for slot in result.slots}) == 9
    assert set(result.alternatives) == {
        (day_index, meal_type)
        for day_index in range(3)
        for meal_type in ("breakfast", "lunch", "dinner")
    }
    assert sum(len(items) for items in result.alternatives.values()) == 45
    for slot in result.slots:
        alternatives = result.alternatives[(slot.day_index, slot.meal_type)]
        assert len({item.recipe.id for item in alternatives}) == 5
        assert slot.recipe.id not in {item.recipe.id for item in alternatives}


def test_three_day_optimizer_returns_typed_insufficiency_for_sparse_catalog():
    profile = IngredientAffinityService().build_profile([], now=datetime.now(UTC))

    result = ThreeDayPlanOptimizer().build_plan(
        [_recipe("breakfast-only", "breakfast", 500)],
        daily_calories=2000,
        affinity=profile,
    )

    assert isinstance(result, MealRecommendationInsufficiency)
    assert result.reason == MealRecommendationInsufficiencyReason.NOT_ENOUGH_CURRENT_RECIPES


def test_optimizer_is_repeatable_for_same_inputs():
    profile = IngredientAffinityService().build_profile([], now=datetime.now(UTC))
    optimizer = ThreeDayPlanOptimizer()
    recipes = _candidate_pool()

    first = optimizer.build_plan(recipes, daily_calories=2000, affinity=profile)
    second = optimizer.build_plan(list(reversed(recipes)), daily_calories=2000, affinity=profile)

    assert not isinstance(first, MealRecommendationInsufficiency)
    assert not isinstance(second, MealRecommendationInsufficiency)
    assert [slot.recipe.id for slot in first.slots] == [
        slot.recipe.id for slot in second.slots
    ]
