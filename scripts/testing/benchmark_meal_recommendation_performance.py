"""Synthetic meal recommendation baseline benchmark.

This script intentionally avoids live databases and user data. It records repeatable
domain-generation and serialization measurements before the performance redesign.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.routes.v1.meal_recommendation_route_support import to_response
from src.domain.model.meal_recommendation import (
    CatalogMeal,
    CatalogMealIngredient,
    MealRecommendationInsufficiency,
    PersistedMealRecommendationCandidate,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityService,
)
from src.domain.services.meal_recommendation.three_day_plan_optimizer import (
    ThreeDayPlanOptimizer,
)

DEFAULT_CATALOG_SIZES = (180, 1000, 5000)
DEFAULT_SAMPLES = 50
DEFAULT_WARMUPS = 10


@dataclass(frozen=True)
class BenchmarkStats:
    p50_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    samples: int


def main() -> None:
    args = _parse_args()
    output = args.output
    sizes = tuple(int(item.strip()) for item in args.catalog_sizes.split(",") if item)
    report = {
        "schema_version": "meal_recommendation_performance_baseline_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "runner": _runner_metadata(),
        "parameters": {
            "catalog_sizes": sizes,
            "warmups": args.warmups,
            "samples": args.samples,
        },
        "results": [
            _benchmark_catalog_size(size, warmups=args.warmups, samples=args.samples)
            for size in sizes
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _benchmark_catalog_size(catalog_size: int, *, warmups: int, samples: int) -> dict:
    catalog = _catalog(catalog_size)
    affinity = IngredientAffinityService().build_profile(
        [], now=datetime(2026, 7, 20, tzinfo=UTC)
    )
    optimizer = ThreeDayPlanOptimizer()

    for _ in range(warmups):
        _build_persisted_plan(optimizer, catalog, affinity)

    generation_durations = []
    serialization_durations = []
    response_sizes = []
    selected_count = 0
    alternative_count = 0
    for _ in range(samples):
        started = perf_counter_ns()
        plan = _build_persisted_plan(optimizer, catalog, affinity)
        generation_durations.append(_elapsed_ms(started))

        started = perf_counter_ns()
        response = to_response(plan)
        response_sizes.append(len(response.model_dump_json().encode("utf-8")))
        serialization_durations.append(_elapsed_ms(started))

        selected_count = len(plan.slots)
        alternative_count = sum(len(slot.alternatives) for slot in plan.slots)

    return {
        "catalog_size": catalog_size,
        "selected_slots": selected_count,
        "alternatives": alternative_count,
        "hydrated_candidate_rows_current_contract": selected_count + alternative_count,
        "catalog_refresh_count_current_contract": samples + warmups,
        "sql_count_current_contract_notes": {
            "create_fresh": "lock + idempotency + full catalog + history + supersede + post-save full batch reload",
            "read": "full batch reload with catalog meal, ingredients, food_reference, serving sizes",
            "synthetic_script_sql_count": 0,
        },
        "response_bytes": {
            "min": min(response_sizes),
            "max": max(response_sizes),
            "last": response_sizes[-1],
        },
        "generation": asdict(_stats(generation_durations)),
        "serialization": asdict(_stats(serialization_durations)),
    }


def _build_persisted_plan(
    optimizer: ThreeDayPlanOptimizer,
    catalog: list[CatalogMeal],
    affinity,
) -> PersistedMealRecommendationPlan:
    result = optimizer.build_plan(catalog, daily_calories=2000, affinity=affinity)
    if isinstance(result, MealRecommendationInsufficiency):
        raise RuntimeError(result.message)

    slots = []
    batch_id = "benchmark-plan"
    start_date = date(2026, 7, 20)
    for position, slot in enumerate(result.slots):
        slot_id = f"slot-{position}"
        selected = PersistedMealRecommendationCandidate(
            id=batch_id if position == 0 else f"selected-{position}",
            slot_id=slot_id,
            recommendation_date=start_date + timedelta(days=slot.day_index),
            meal_type=slot.meal_type,
            catalog_meal_id=slot.catalog_meal.id,
            candidate_rank=0,
            is_selected=True,
            score=Decimal(str(slot.score)),
            selection_version=1,
            catalog_meal=slot.catalog_meal,
        )
        alternatives = tuple(
            PersistedMealRecommendationCandidate(
                id=f"alternative-{position}-{alternative_position}",
                slot_id=slot_id,
                recommendation_date=start_date + timedelta(days=slot.day_index),
                meal_type=slot.meal_type,
                catalog_meal_id=alternative.catalog_meal.id,
                candidate_rank=alternative_position + 1,
                is_selected=False,
                score=Decimal(str(alternative.score)),
                selection_version=1,
                catalog_meal=alternative.catalog_meal,
            )
            for alternative_position, alternative in enumerate(
                result.alternatives[(slot.day_index, slot.meal_type)]
            )
        )
        slots.append(
            PersistedMealRecommendationSlot(
                id=slot_id,
                slot_date=start_date + timedelta(days=slot.day_index),
                day_index=slot.day_index,
                meal_type=slot.meal_type,
                catalog_meal_id=slot.catalog_meal.id,
                target_calories=slot.target_calories,
                score=slot.score,
                position=position,
                selected=selected,
                alternatives=alternatives,
            )
        )

    return PersistedMealRecommendationPlan(
        id=batch_id,
        user_id="synthetic-user",
        status="active",
        timezone="UTC",
        start_date=start_date,
        daily_calories=2000,
        algorithm_version=result.algorithm_version,
        operation="three_day",
        idempotency_key="synthetic-key",
        request_fingerprint="f" * 64,
        slots=tuple(slots),
    )


def _catalog(size: int) -> list[CatalogMeal]:
    meal_types = ("breakfast", "lunch", "dinner")
    targets = {"breakfast": 500, "lunch": 750, "dinner": 750}
    catalog = []
    for index in range(size):
        meal_type = meal_types[index % len(meal_types)]
        calories = targets[meal_type] + (index // len(meal_types)) % 25
        catalog.append(
            CatalogMeal(
                id=f"{meal_type}-{index:04d}",
                catalog_key=f"key-{index:04d}",
                content_hash=f"{index:064d}"[:64],
                name=f"{meal_type.title()} Recipe {index:04d}",
                cuisine="vietnamese",
                description="Synthetic benchmark recipe",
                image_url=None,
                protein_g=Decimal(str(calories / 4)),
                carbs_g=Decimal("0"),
                fat_g=Decimal("0"),
                fiber_g=Decimal("0"),
                meal_types=(meal_type,),
                ingredients=(
                    CatalogMealIngredient(
                        food_reference_id=index + 1,
                        display_name="Synthetic ingredient",
                        quantity=Decimal("100"),
                        unit="g",
                    ),
                ),
            )
        )
    return catalog


def _stats(values: list[float]) -> BenchmarkStats:
    sorted_values = sorted(values)
    return BenchmarkStats(
        p50_ms=round(statistics.median(sorted_values), 4),
        p95_ms=round(_percentile(sorted_values, 0.95), 4),
        min_ms=round(sorted_values[0], 4),
        max_ms=round(sorted_values[-1], 4),
        samples=len(sorted_values),
    )


def _percentile(values: list[float], percentile: float) -> float:
    index = int(round((len(values) - 1) * percentile))
    return values[index]


def _elapsed_ms(started_ns: int) -> float:
    return (perf_counter_ns() - started_ns) / 1_000_000


def _runner_metadata() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-sizes", default=",".join(map(str, DEFAULT_CATALOG_SIZES)))
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plans/reports/meal-recommendation-performance-baseline.json"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
