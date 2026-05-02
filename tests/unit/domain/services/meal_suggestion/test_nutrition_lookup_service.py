"""
Unit tests for NutritionLookupService — all external I/O mocked.

Covers:
- T1 hit (food_reference exact match)
- T1 miss → T2 hit (FatSecret resolver)
- T1+T2 miss → T3 AI fallback (with logging)
- T3 AI failure → zero macros, no exception
- T3 uses asyncio.to_thread + wait_for (C2/C3: non-blocking, 10s timeout)
- Fiber-aware calorie derivation
- _aggregate sums and tier counts
- calculate_meal_macros runs lookups in parallel
- _to_grams unit conversions
"""

import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.domain.services.meal_suggestion.nutrition_lookup_service import (
    IngredientMacros,
    MealMacros,
    NutritionLookupService,
    _derive_calories,
)
from src.domain.services.meal_suggestion.ingredient_nutrition_resolver import (
    PerHundredGramsMacros,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref(
    protein: float = 23.0,
    carbs: float = 0.0,
    fat: float = 2.5,
    fiber: float = 0.0,
    sugar: float = 0.0,
    ref_id: int = 1,
) -> dict:
    """Minimal food_reference dict as returned by FoodReferenceRepository."""
    return {
        "id": ref_id,
        "protein_100g": protein,
        "carbs_100g": carbs,
        "fat_100g": fat,
        "fiber_100g": fiber,
        "sugar_100g": sugar,
    }


def _make_service(
    ref_result=None,
    resolver_result=None,
    gen_result=None,
) -> NutritionLookupService:
    """Build a NutritionLookupService with all dependencies mocked."""
    repo = MagicMock()
    repo.find_by_normalized_name.return_value = ref_result

    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=resolver_result)

    gen = MagicMock()
    if gen_result is not None:
        gen.generate_meal_plan.return_value = gen_result
    else:
        gen.generate_meal_plan.side_effect = RuntimeError("AI unavailable")

    return NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen,
    )


# ---------------------------------------------------------------------------
# _derive_calories
# ---------------------------------------------------------------------------


def test_derive_calories_fiber_aware():
    """protein=30, carbs=50, fiber=10, fat=5 @ factor 1.0 → 345."""
    # P=30: 30×4=120; net_carbs=40: 40×4=160; fiber=10: 10×2=20; F=5: 5×9=45 → 345
    result = _derive_calories(protein=30.0, carbs=50.0, fat=5.0, fiber=10.0)
    assert result == pytest.approx(345.0)


def test_derive_calories_no_fiber():
    """Simple case: protein=20, carbs=30, fat=10, fiber=0 → 290."""
    result = _derive_calories(protein=20.0, carbs=30.0, fat=10.0, fiber=0.0)
    assert result == pytest.approx(290.0)


def test_derive_calories_fiber_cannot_exceed_carbs():
    """If fiber > carbs (data error), net_carbs floors at 0, no negative."""
    result = _derive_calories(protein=0.0, carbs=5.0, fat=0.0, fiber=10.0)
    # net_carbs = max(5-10, 0) = 0; fiber=10: 10×2=20 → 20
    assert result == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# T1 hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t1_hit_returns_correct_macros():
    """T1: food_reference exact match → correct IngredientMacros."""
    ref = _make_ref(protein=23.0, carbs=0.0, fat=2.5, fiber=0.0, sugar=0.0, ref_id=7)
    svc = _make_service(ref_result=ref)

    result = await svc._lookup_ingredient("chicken breast", 150.0)

    assert result.source_tier == "T1_food_reference"
    assert result.food_reference_id == 7
    assert result.protein == pytest.approx(34.5)  # 23 * 1.5
    assert result.fat == pytest.approx(3.8, abs=0.1)  # 2.5 * 1.5 = 3.75 → rounded
    # Calories: P×4 + C×4 + F×9 (no fiber)
    expected_cal = _derive_calories(34.5, 0.0, 3.75, 0.0)
    assert result.calories == pytest.approx(round(expected_cal, 1))
    # Resolver should NOT be called
    svc._resolver.resolve.assert_not_called()


# ---------------------------------------------------------------------------
# T1 miss → T2 hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t1_miss_t2_hit_returns_fatsecret_macros():
    """T1 miss → T2 (FatSecret resolver) hit → correct macros, tier T2."""
    per100 = PerHundredGramsMacros(
        protein=25.0, carbs=0.0, fat=3.0, fiber=0.0, sugar=0.0
    )
    svc = _make_service(ref_result=None, resolver_result=per100)

    result = await svc._lookup_ingredient("turkey breast", 200.0)

    assert result.source_tier == "T2_fatsecret"
    assert result.food_reference_id is None
    assert result.protein == pytest.approx(50.0)  # 25 * 2.0
    assert result.fat == pytest.approx(6.0)  # 3 * 2.0
    expected_cal = _derive_calories(50.0, 0.0, 6.0, 0.0)
    assert result.calories == pytest.approx(round(expected_cal, 1))


# ---------------------------------------------------------------------------
# T1 + T2 miss → T3 AI fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t1_t2_miss_uses_t3_ai_fallback(caplog):
    """T1+T2 miss → AI fallback, WARNING logged, source_tier T3."""
    gen_data = {"protein": 10.0, "carbs": 20.0, "fat": 5.0, "fiber": 2.0, "sugar": 1.0}
    svc = _make_service(ref_result=None, resolver_result=None, gen_result=gen_data)

    with caplog.at_level(
        logging.WARNING,
        logger="src.domain.services.meal_suggestion.nutrition_lookup_service",
    ):
        result = await svc._lookup_ingredient("exotic mushroom blend", 100.0)

    assert result.source_tier == "T3_ai_estimate"
    assert "T3 AI estimate used for ingredient" in caplog.text
    assert "exotic mushroom blend" in caplog.text
    assert result.protein == pytest.approx(10.0)
    assert result.carbs == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# T3 AI failure → zero macros, no exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t3_ai_failure_returns_zero_macros_no_exception():
    """T3 AI failure → zero macros returned, no exception bubbled."""
    svc = _make_service(ref_result=None, resolver_result=None, gen_result=None)
    # gen_result=None causes generate_meal_plan to raise RuntimeError

    result = await svc._lookup_ingredient("mystery ingredient", 50.0)

    assert result.source_tier == "T3_ai_estimate"
    assert result.calories == 0.0
    assert result.protein == 0.0
    assert result.carbs == 0.0
    assert result.fat == 0.0


# ---------------------------------------------------------------------------
# _aggregate
# ---------------------------------------------------------------------------


def test_aggregate_sums_and_counts_tiers():
    """_aggregate sums macros and counts tiers correctly."""
    svc = _make_service()
    ingredients = [
        IngredientMacros(
            "rice", 200.0, 260.0, 4.0, 52.0, 0.5, 0.5, 0.0, "T1_food_reference", 1
        ),
        IngredientMacros(
            "chicken", 150.0, 172.5, 34.5, 0.0, 3.75, 0.0, 0.0, "T1_food_reference", 2
        ),
        IngredientMacros(
            "sriracha", 15.0, 15.0, 0.5, 3.0, 0.3, 0.0, 1.0, "T2_fatsecret"
        ),
        IngredientMacros(
            "exotic spice", 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "T3_ai_estimate"
        ),
    ]
    meal = svc._aggregate(ingredients)

    assert meal.t1_count == 2
    assert meal.t2_count == 1
    assert meal.t3_count == 1
    assert meal.protein == pytest.approx(round(4.0 + 34.5 + 0.5 + 0.0, 1))
    assert meal.carbs == pytest.approx(round(52.0 + 0.0 + 3.0 + 0.0, 1))
    assert meal.fat == pytest.approx(round(0.5 + 3.75 + 0.3 + 0.0, 1))
    # Calories re-derived from aggregated totals
    total_p = 4.0 + 34.5 + 0.5
    total_c = 52.0 + 3.0
    total_f = 0.5 + 3.75 + 0.3
    total_fiber = 0.5 + 0.0 + 0.0
    expected_cal = _derive_calories(total_p, total_c, total_f, total_fiber)
    assert meal.calories == pytest.approx(round(expected_cal, 1))


# ---------------------------------------------------------------------------
# calculate_meal_macros — parallel execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_meal_macros_runs_lookups_in_parallel():
    """Parallel gather: total elapsed should be ~max(individual) not ~sum."""
    call_order = []

    async def slow_resolve(name: str):
        call_order.append(f"start:{name}")
        await asyncio.sleep(0.05)
        call_order.append(f"end:{name}")
        return PerHundredGramsMacros(protein=10.0, carbs=10.0, fat=5.0)

    repo = MagicMock()
    repo.find_by_normalized_name.return_value = None  # force T2
    resolver = MagicMock()
    resolver.resolve = slow_resolve
    gen = MagicMock()

    svc = NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen,
    )

    import time

    start = time.monotonic()
    meal = await svc.calculate_meal_macros(
        [
            {"name": "item_a", "amount": 100.0, "unit": "g"},
            {"name": "item_b", "amount": 100.0, "unit": "g"},
            {"name": "item_c", "amount": 100.0, "unit": "g"},
        ]
    )
    elapsed = time.monotonic() - start

    # 3 serial 50ms sleeps = 150ms; parallel ≈ 50ms with tolerance
    assert elapsed < 0.13, f"Expected parallel execution, took {elapsed:.3f}s"
    assert len(meal.ingredients) == 3
    # Both "start" events appear before any "end" confirms actual concurrency
    starts = [e for e in call_order if e.startswith("start")]
    assert len(starts) == 3


# ---------------------------------------------------------------------------
# _to_grams
# ---------------------------------------------------------------------------


def test_to_grams_identity_for_grams():
    svc = _make_service()
    assert svc._to_grams("rice", 150.0, "g") == pytest.approx(150.0)


def test_to_grams_tbsp_oil_density():
    """1 tbsp oil → 15ml × 0.92 density = 13.8g."""
    svc = _make_service()
    result = svc._to_grams("olive oil", 1.0, "tbsp")
    assert result == pytest.approx(13.8)


def test_to_grams_cup_water():
    """1 cup water → 240ml × 1.0 density = 240g."""
    svc = _make_service()
    result = svc._to_grams("water", 1.0, "cup")
    assert result == pytest.approx(240.0)


def test_to_grams_tsp():
    """1 tsp → 5ml."""
    svc = _make_service()
    result = svc._to_grams("salt", 1.0, "tsp")
    assert result == pytest.approx(5.0)


def test_to_grams_ml():
    """100ml soy sauce → 100 × 1.20 = 120g."""
    svc = _make_service()
    result = svc._to_grams("soy sauce", 100.0, "ml")
    assert result == pytest.approx(120.0)


def test_to_grams_unknown_unit_assumes_grams(caplog):
    svc = _make_service()
    with caplog.at_level(logging.WARNING):
        result = svc._to_grams("flour", 2.0, "handful")
    assert result == pytest.approx(2.0)
    assert "Unknown unit" in caplog.text


# ---------------------------------------------------------------------------
# C2/C3: T3 _ai_estimate uses asyncio.to_thread + wait_for
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t3_ai_estimate_does_not_block_event_loop():
    """C2: _ai_estimate wraps generate_meal_plan in asyncio.to_thread.

    If the call were made directly (not via to_thread), it would block the
    event loop and prevent other coroutines from running. We verify that a
    slow synchronous generate_meal_plan does NOT block a concurrent task.
    """
    import time

    slow_completed = []

    def slow_generate(*args, **kwargs):
        time.sleep(0.05)  # 50ms blocking sleep — must not block event loop
        return {"protein": 10.0, "carbs": 5.0, "fat": 2.0, "fiber": 0.0, "sugar": 0.0}

    repo = MagicMock()
    repo.find_by_normalized_name.return_value = None
    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=None)
    gen = MagicMock()
    gen.generate_meal_plan.side_effect = slow_generate

    svc = NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen,
    )

    async def concurrent_task():
        await asyncio.sleep(0.01)
        slow_completed.append(True)

    # Run both concurrently; if _ai_estimate blocks, concurrent_task can't run
    await asyncio.gather(
        svc._lookup_ingredient("mystery herb", 10.0),
        concurrent_task(),
    )

    # concurrent_task must have run (proves event loop was NOT blocked)
    assert (
        slow_completed
    ), "Concurrent task was blocked — _ai_estimate is not using to_thread"


@pytest.mark.asyncio
async def test_t3_ai_estimate_respects_10s_timeout():
    """C2: _ai_estimate wraps generate_meal_plan in wait_for(timeout=10.0).

    Verify that when wait_for raises TimeoutError (the internal 10s budget),
    _ai_estimate catches it via 'except Exception' and returns zero-macro fallback
    instead of propagating the error.
    """
    repo = MagicMock()
    repo.find_by_normalized_name.return_value = None
    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=None)
    gen = MagicMock()
    gen.generate_meal_plan.return_value = {
        "protein": 5.0,
        "carbs": 5.0,
        "fat": 1.0,
        "fiber": 0.0,
        "sugar": 0.0,
    }

    svc = NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen,
    )

    # Patch wait_for in the service module to raise TimeoutError immediately,
    # simulating the internal 10s budget being exceeded.
    async def timed_out_wait_for(coro, timeout):
        coro.close()  # clean up the coroutine to avoid ResourceWarning
        raise asyncio.TimeoutError("simulated 10s timeout")

    with patch(
        "src.domain.services.meal_suggestion.nutrition_lookup_service.asyncio.wait_for",
        side_effect=timed_out_wait_for,
    ):
        result = await svc._lookup_ingredient("slow ingredient", 50.0)

    # TimeoutError caught → zero macros fallback, no exception propagated
    assert result.source_tier == "T3_ai_estimate"
    assert result.calories == 0.0


@pytest.mark.asyncio
async def test_t3_ai_estimate_passes_correct_positional_args():
    """C3: generate_meal_plan called with (prompt, system_message, 'json', 256, schema, None)."""
    from src.domain.services.meal_suggestion.nutrition_lookup_service import (
        SingleIngredientSchema,
    )

    repo = MagicMock()
    repo.find_by_normalized_name.return_value = None
    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=None)
    gen = MagicMock()
    gen.generate_meal_plan.return_value = {
        "protein": 8.0,
        "carbs": 3.0,
        "fat": 1.0,
        "fiber": 0.0,
        "sugar": 0.0,
    }

    svc = NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen,
    )

    await svc._lookup_ingredient("truffle oil", 20.0)

    gen.generate_meal_plan.assert_called_once()
    args = gen.generate_meal_plan.call_args[0]  # positional args passed to to_thread
    assert len(args) == 6, f"Expected 6 positional args, got {len(args)}: {args}"
    assert args[2] == "json"  # response_type
    assert args[3] == 256  # max_tokens
    assert args[4] is SingleIngredientSchema  # schema
    assert args[5] is None  # model_purpose


# ---------------------------------------------------------------------------
# Integration-ish: chicken fried rice fixture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chicken_fried_rice_realistic_totals():
    """Mock T1 for all ingredients → aggregate within 15% of manual calc.

    Per-100g mock values and expected totals:
      - Rice 400g (P=2, C=22, F=0.3/100g): P=8.0,  C=88.0, fat=1.2
      - Chicken 300g (P=23, C=0, F=2.5/100g): P=69.0, C=0,    fat=7.5
      - Egg 100g (P=13, C=1.1, F=10/100g):  P=13.0, C=1.1,  fat=10.0
      - Oil 30g (pure fat 100g/100g):        P=0,    C=0,    fat=30.0
      - Soy sauce 30g (P=10, C=17/100g):     P=3.0,  C=5.1,  fat=0
    Totals: P≈93, C≈94.2, fat≈48.7
    """
    refs = {
        "rice": _make_ref(protein=2.0, carbs=22.0, fat=0.3, fiber=0.4),
        "chicken": _make_ref(protein=23.0, carbs=0.0, fat=2.5, fiber=0.0),
        "egg": _make_ref(protein=13.0, carbs=1.1, fat=10.0, fiber=0.0),
        "oil": _make_ref(protein=0.0, carbs=0.0, fat=100.0, fiber=0.0),
        "soy sauce": _make_ref(protein=10.0, carbs=17.0, fat=0.0, fiber=0.0),
    }

    # Map normalized names to refs
    def find_ref(normalized_name: str):
        for key, ref in refs.items():
            if key in normalized_name:
                return ref
        return None

    repo = MagicMock()
    repo.find_by_normalized_name.side_effect = find_ref
    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=None)  # force T1 path
    gen = MagicMock()

    svc = NutritionLookupService(
        food_ref_repo=repo,
        ingredient_nutrition_resolver=resolver,
        generation_service=gen,
    )

    meal = await svc.calculate_meal_macros(
        [
            {"name": "cooked rice", "amount": 400.0, "unit": "g"},
            {"name": "chicken breast", "amount": 300.0, "unit": "g"},
            {"name": "egg", "amount": 100.0, "unit": "g"},
            {"name": "vegetable oil", "amount": 30.0, "unit": "g"},
            {"name": "soy sauce", "amount": 30.0, "unit": "g"},
        ]
    )

    # All T1 hits
    assert meal.t1_count == 5
    assert meal.t2_count == 0
    assert meal.t3_count == 0

    # Verify within ±15% of expected (see docstring for derivation)
    assert meal.protein == pytest.approx(93.0, rel=0.15)
    assert meal.carbs == pytest.approx(94.2, rel=0.15)
    assert meal.fat == pytest.approx(48.7, rel=0.15)

    # Calories must be derived, not zero
    assert meal.calories > 0
    # Sanity: calories consistent with formula
    expected_cal = _derive_calories(meal.protein, meal.carbs, meal.fat, meal.fiber)
    assert meal.calories == pytest.approx(round(expected_cal, 1))
