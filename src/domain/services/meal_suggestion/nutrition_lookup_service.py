"""
Three-tier nutrition lookup orchestration service.

Tier resolution order per ingredient:
  Redis — cached per-100g macros (24-hour TTL)
  T1 — exact match on food_reference.name_normalized (MySQL, no fuzzy)
  T2 — FatSecret via IngredientNutritionResolver (caches result to T1)
  T3 — AI single-ingredient estimate (last resort, logged as WARNING)

Calories are ALWAYS derived: P×4 + (C−fiber)×4 + fiber×2 + F×9
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.domain.constants.food_density import get_density
from src.domain.services.meal_suggestion.ingredient_name_normalizer import normalize_food_name

logger = logging.getLogger(__name__)

NUTRITION_CACHE_TTL = 86400  # 24 hours
T2_TIMEOUT = 2.0  # FatSecret timeout
T3_TIMEOUT = 3.0  # AI estimate timeout

# Volume conversions: unit → millilitres
_VOLUME_TO_ML: Dict[str, float] = {"cup": 240.0, "tbsp": 15.0, "tsp": 5.0}


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IngredientMacros:
    """Calculated macros for a specific ingredient quantity."""

    name: str
    quantity_g: float
    calories: float       # derived: P×4 + (C−fiber)×4 + fiber×2 + F×9
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    source_tier: str      # "T1_food_reference" | "T2_fatsecret" | "T3_ai_estimate"
    food_reference_id: Optional[int] = field(default=None)


@dataclass
class MealMacros:
    """Aggregated macros for an entire meal."""

    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    ingredients: List[IngredientMacros]
    t1_count: int   # resolved via food_reference
    t2_count: int   # resolved via FatSecret
    t3_count: int   # resolved via AI fallback


# ---------------------------------------------------------------------------
# Pydantic schema for T3 AI structured output
# ---------------------------------------------------------------------------

class SingleIngredientSchema(BaseModel):
    """Per-100g macros returned by the AI for a single ingredient."""

    protein: float = Field(..., ge=0)
    carbs: float = Field(..., ge=0)
    fat: float = Field(..., ge=0)
    fiber: float = Field(default=0.0, ge=0)
    sugar: float = Field(default=0.0, ge=0)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class NutritionLookupService:
    """Resolve macros for meal ingredients using three-tier lookup."""

    def __init__(
        self,
        food_ref_repo: Any,
        ingredient_nutrition_resolver: Any,
        generation_service: Any,
        redis_client: Any = None,
    ) -> None:
        self._repo = food_ref_repo
        self._resolver = ingredient_nutrition_resolver
        self._gen = generation_service
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate_meal_macros(
        self, ingredients: List[Dict[str, Any]]
    ) -> MealMacros:
        """Calculate deterministic macros for a list of ingredients.

        Args:
            ingredients: [{"name": str, "amount": float, "unit": str}, ...]

        Returns:
            MealMacros with aggregated totals and per-ingredient breakdown.
        """
        tasks = [
            self._lookup_ingredient(
                ing["name"],
                self._to_grams(ing["name"], float(ing["amount"]), ing["unit"]),
            )
            for ing in ingredients
        ]
        results: List[IngredientMacros] = await asyncio.gather(*tasks)
        return self._aggregate(list(results))

    # ------------------------------------------------------------------
    # Three-tier lookup
    # ------------------------------------------------------------------

    async def _lookup_ingredient(
        self, name: str, quantity_g: float
    ) -> IngredientMacros:
        """Resolve macros for one ingredient: Redis → T1 → T2 → T3."""
        normalized = normalize_food_name(name)
        cache_key = f"nutrition:{normalized}"

        # Check Redis cache first
        if self._redis:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return self._build_from_cached(data, name, quantity_g)
            except Exception as exc:
                logger.warning("Redis get failed for %s: %s", cache_key, exc)

        # T1: exact match on name_normalized
        ref = self._repo.find_by_normalized_name(normalized)
        if ref:
            result = self._calculate_from_ref(ref, name, quantity_g, "T1_food_reference")
            await self._cache_result(cache_key, result)
            return result

        # T2: FatSecret (resolver handles caching to food_reference)
        try:
            per100 = await asyncio.wait_for(
                self._resolver.resolve(name), timeout=T2_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning("T2 FatSecret timeout for %s", name)
            per100 = None
        if per100 is not None:
            result = self._build_from_per100(per100, name, quantity_g, "T2_fatsecret")
            await self._cache_result(cache_key, result)
            return result

        # T3: AI estimate — last resort
        try:
            result = await asyncio.wait_for(
                self._ai_estimate(name, quantity_g), timeout=T3_TIMEOUT
            )
            await self._cache_result(cache_key, result)
            return result
        except asyncio.TimeoutError:
            logger.warning("T3 AI timeout for %s", name)
            return IngredientMacros(
                name=name,
                quantity_g=round(quantity_g, 1),
                calories=0.0,
                protein=0.0,
                carbs=0.0,
                fat=0.0,
                fiber=0.0,
                sugar=0.0,
                source_tier="T3_ai_estimate",
            )

    # ------------------------------------------------------------------
    # Redis cache helpers
    # ------------------------------------------------------------------

    def _build_from_cached(
        self, data: Dict[str, Any], name: str, quantity_g: float
    ) -> IngredientMacros:
        """Build IngredientMacros from cached per-100g data."""
        factor = quantity_g / 100.0
        protein = data["protein"] * factor
        carbs = data["carbs"] * factor
        fat = data["fat"] * factor
        fiber = data.get("fiber", 0.0) * factor
        sugar = data.get("sugar", 0.0) * factor
        calories = _derive_calories(protein, carbs, fat, fiber)
        return IngredientMacros(
            name=name,
            quantity_g=round(quantity_g, 1),
            calories=round(calories, 1),
            protein=round(protein, 1),
            carbs=round(carbs, 1),
            fat=round(fat, 1),
            fiber=round(fiber, 1),
            sugar=round(sugar, 1),
            source_tier=data.get("source_tier", "cached"),
        )

    async def _cache_result(self, key: str, result: IngredientMacros) -> None:
        """Cache per-100g macros in Redis."""
        if not self._redis:
            return
        try:
            factor = 100.0 / result.quantity_g if result.quantity_g > 0 else 1.0
            data = {
                "protein": round(result.protein * factor, 2),
                "carbs": round(result.carbs * factor, 2),
                "fat": round(result.fat * factor, 2),
                "fiber": round(result.fiber * factor, 2),
                "sugar": round(result.sugar * factor, 2),
                "source_tier": result.source_tier,
            }
            await self._redis.setex(key, NUTRITION_CACHE_TTL, json.dumps(data))
        except Exception as exc:
            logger.warning("Redis setex failed for %s: %s", key, exc)

    # ------------------------------------------------------------------
    # Calculation helpers
    # ------------------------------------------------------------------

    def _calculate_from_ref(
        self,
        ref: Dict[str, Any],
        name: str,
        quantity_g: float,
        tier: str,
    ) -> IngredientMacros:
        """Scale per-100g values from a food_reference dict to quantity_g."""
        factor = quantity_g / 100.0
        protein = (ref.get("protein_100g") or 0.0) * factor
        carbs = (ref.get("carbs_100g") or 0.0) * factor
        fat = (ref.get("fat_100g") or 0.0) * factor
        fiber = (ref.get("fiber_100g") or 0.0) * factor
        sugar = (ref.get("sugar_100g") or 0.0) * factor
        calories = _derive_calories(protein, carbs, fat, fiber)
        return IngredientMacros(
            name=name,
            quantity_g=round(quantity_g, 1),
            calories=round(calories, 1),
            protein=round(protein, 1),
            carbs=round(carbs, 1),
            fat=round(fat, 1),
            fiber=round(fiber, 1),
            sugar=round(sugar, 1),
            source_tier=tier,
            food_reference_id=ref.get("id"),
        )

    def _build_from_per100(
        self,
        per100: Any,   # PerHundredGramsMacros from ingredient_nutrition_resolver
        name: str,
        quantity_g: float,
        tier: str,
    ) -> IngredientMacros:
        """Build IngredientMacros from a PerHundredGramsMacros dataclass."""
        factor = quantity_g / 100.0
        protein = per100.protein * factor
        carbs = per100.carbs * factor
        fat = per100.fat * factor
        fiber = per100.fiber * factor
        sugar = per100.sugar * factor
        calories = _derive_calories(protein, carbs, fat, fiber)
        return IngredientMacros(
            name=name,
            quantity_g=round(quantity_g, 1),
            calories=round(calories, 1),
            protein=round(protein, 1),
            carbs=round(carbs, 1),
            fat=round(fat, 1),
            fiber=round(fiber, 1),
            sugar=round(sugar, 1),
            source_tier=tier,
            food_reference_id=None,
        )

    async def _ai_estimate(
        self, name: str, quantity_g: float
    ) -> IngredientMacros:
        """T3 fallback: ask AI for per-100g macros. Never raises."""
        logger.warning("T3 AI estimate used for ingredient: %s", name)

        prompt = (
            f"What are the macros per 100g for '{name}'? "
            "Return JSON with keys: protein, carbs, fat, fiber, sugar (all floats, grams)."
        )
        system_message = (
            "You are a nutrition database assistant. "
            "Return only JSON with per-100g macros."
        )

        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(
                    self._gen.generate_meal_plan,
                    prompt,
                    system_message,
                    "json",
                    256,
                    SingleIngredientSchema,
                    None,
                ),
                timeout=10.0,
            )
            # generate_meal_plan returns a dict when schema is provided
            schema_data = SingleIngredientSchema(**raw) if isinstance(raw, dict) else raw
            return self._build_from_per100(schema_data, name, quantity_g, "T3_ai_estimate")
        except Exception as exc:
            logger.error(
                "T3 AI estimate failed for ingredient '%s': %s", name, exc
            )
            return IngredientMacros(
                name=name,
                quantity_g=round(quantity_g, 1),
                calories=0.0,
                protein=0.0,
                carbs=0.0,
                fat=0.0,
                fiber=0.0,
                sugar=0.0,
                source_tier="T3_ai_estimate",
            )

    # ------------------------------------------------------------------
    # Unit conversion
    # ------------------------------------------------------------------

    def _to_grams(self, name: str, amount: float, unit: str) -> float:
        """Convert amount+unit to grams using food density when needed."""
        unit_lower = unit.lower().strip()

        if unit_lower == "g":
            return amount

        if unit_lower == "ml":
            return amount * get_density(name)

        if unit_lower in _VOLUME_TO_ML:
            ml = amount * _VOLUME_TO_ML[unit_lower]
            return ml * get_density(name)

        # Unknown unit — assume grams
        logger.warning(
            "Unknown unit '%s' for ingredient '%s'; assuming grams", unit, name
        )
        return amount

    # ------------------------------------------------------------------
    # Calorie scaling
    # ------------------------------------------------------------------

    def scale_to_target(
        self, meal_macros: MealMacros, target_calories: int
    ) -> Optional[MealMacros]:
        """Scale ingredient quantities so total calories ≈ target_calories.

        Returns scaled MealMacros, or None if scale factor is outside 0.7–1.4
        (caller should regenerate the recipe).

        Edge cases:
          - meal_macros.calories <= 0: return None — zero-cal recipes cannot be scaled
            and must not be served (caller should reject the recipe).
          - target_calories <= 0: return meal_macros unchanged, log warning
            (programming bug; different from a zero-cal ingredient result).
        """
        if target_calories <= 0:
            logger.warning(
                "scale_to_target: target_calories=%d is invalid, returning macros unchanged",
                target_calories,
            )
            return meal_macros

        if meal_macros.calories <= 0:
            logger.warning(
                "scale_to_target: meal has 0 kcal (all T3 lookups failed?) — rejecting recipe"
            )
            return None

        scale = target_calories / meal_macros.calories

        if scale < 0.7 or scale > 1.4:
            logger.warning(
                "scale_to_target: scale factor %.2f out of range [0.7, 1.4] "
                "(actual=%.1f kcal, target=%d kcal) — recipe rejected",
                scale,
                meal_macros.calories,
                target_calories,
            )
            return None

        scaled_ingredients = [
            IngredientMacros(
                name=ing.name,
                quantity_g=round(ing.quantity_g * scale, 1),
                calories=0.0,  # re-derived by _aggregate
                protein=round(ing.protein * scale, 1),
                carbs=round(ing.carbs * scale, 1),
                fat=round(ing.fat * scale, 1),
                fiber=round(ing.fiber * scale, 1),
                sugar=round(ing.sugar * scale, 1),
                source_tier=ing.source_tier,
                food_reference_id=ing.food_reference_id,
            )
            for ing in meal_macros.ingredients
        ]
        return self._aggregate(scaled_ingredients)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate(self, ingredients: List[IngredientMacros]) -> MealMacros:
        """Sum ingredient macros and count tier hits."""
        total_protein = sum(i.protein for i in ingredients)
        total_carbs = sum(i.carbs for i in ingredients)
        total_fat = sum(i.fat for i in ingredients)
        total_fiber = sum(i.fiber for i in ingredients)
        total_sugar = sum(i.sugar for i in ingredients)
        total_calories = _derive_calories(
            total_protein, total_carbs, total_fat, total_fiber
        )

        return MealMacros(
            calories=round(total_calories, 1),
            protein=round(total_protein, 1),
            carbs=round(total_carbs, 1),
            fat=round(total_fat, 1),
            fiber=round(total_fiber, 1),
            sugar=round(total_sugar, 1),
            ingredients=ingredients,
            t1_count=sum(1 for i in ingredients if i.source_tier == "T1_food_reference"),
            t2_count=sum(1 for i in ingredients if i.source_tier == "T2_fatsecret"),
            t3_count=sum(1 for i in ingredients if i.source_tier == "T3_ai_estimate"),
        )


# ---------------------------------------------------------------------------
# Module-level utility
# ---------------------------------------------------------------------------

def _derive_calories(
    protein: float, carbs: float, fat: float, fiber: float
) -> float:
    """Fiber-aware calorie derivation: P×4 + (C−fiber)×4 + fiber×2 + F×9."""
    net_carbs = max(carbs - fiber, 0.0)
    return protein * 4.0 + net_carbs * 4.0 + fiber * 2.0 + fat * 9.0
