"""
Nutrition calculation service - domain service for nutrition-related operations.
Provides a unified interface for calculating nutrition from various sources.
"""
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from src.domain.constants.food_density import get_density, DEFAULT_DENSITY
from src.domain.model.nutrition import FoodItem, Nutrition
from src.domain.model.nutrition import Macros
from src.domain.model.nutrition.serving_unit import ServingUnit

logger = logging.getLogger(__name__)

# Shared unit-to-grams conversion table for common serving units.
# Used by both parse-text and manual-meal handlers to ensure consistent nutrition.
UNIT_TO_GRAMS = {
    "large": 50.0,     # ~50g per large egg
    "medium": 44.0,    # ~44g per medium egg
    "small": 38.0,     # ~38g per small egg
    "cup": 240.0,
    "tablespoon": 15.0,
    "tbsp": 15.0,
    "teaspoon": 5.0,
    "tsp": 5.0,
    "piece": 100.0,
    "slice": 30.0,
    "serving": 100.0,
    "kg": 1000.0,
    "lb": 453.6,
    "oz": 28.35,
    # ml/l removed — handled by density-aware logic in convert_quantity_to_grams
}


def _normalize_unit(unit: str) -> str:
    """Normalize unit string: strip qualifiers, handle plurals, lowercase."""
    unit = (unit or "g").lower().strip()
    # Strip common qualifiers (e.g., "cup cooked" → "cup", "medium ripe" → "medium")
    base = unit.split()[0] if " " in unit else unit
    # Handle plurals (e.g., "tablespoons" → "tablespoon", "cups" → "cup")
    if base.endswith("s") and base not in UNIT_TO_GRAMS:
        singular = base[:-1]
        if singular in UNIT_TO_GRAMS:
            return singular
    return base


def convert_quantity_to_grams(
    quantity: float, unit: str, food_name: str = ""
) -> float:
    """Convert a quantity+unit pair to grams.

    For volume units (ml, l), applies food-specific density from
    ``food_density.get_density``.  Weight/count units use the global
    ``UNIT_TO_GRAMS`` mapping.
    """
    normalized = _normalize_unit(unit)
    if normalized == "g":
        return quantity

    # Volume units — apply density
    if normalized in ("ml", "l", "liter", "litre"):
        base_ml = quantity if normalized == "ml" else quantity * 1000
        density = get_density(food_name) if food_name else DEFAULT_DENSITY
        return base_ml * density

    grams_per_unit = UNIT_TO_GRAMS.get(normalized)
    if grams_per_unit is None:
        logger.warning(
            f"Unknown unit '{unit}' (normalized: '{normalized}') — treating quantity as grams"
        )
        return quantity
    return quantity * grams_per_unit



def scale_per_100g_nutrition(
    per_100g: dict,
    quantity: float,
    unit: str,
    base_serving: float = 100.0,
    allowed_units: Optional[List[Dict[str, Any]]] = None,
    food_name: str = "",
) -> dict:
    """Scale per-100g nutrition values for a given quantity and unit.

    Args:
        per_100g: Dict with per-100g nutrition values (calories, protein, carbs, fat)
        quantity: The quantity amount
        unit: The unit name (e.g., "cup", "g", "piece")
        base_serving: The base serving size in grams (default 100g)
        allowed_units: Optional list of allowed ServingUnits for the food
        food_name: Food name for density-aware ml→g conversion

    Returns:
        dict with keys: calories, protein, carbs, fat.
    """
    # Use food-specific allowed_units if available, otherwise fallback to global mapping
    if allowed_units:
        quantity_in_grams = _convert_with_allowed_units(quantity, unit, allowed_units, food_name)
    else:
        quantity_in_grams = convert_quantity_to_grams(quantity, unit, food_name)

    factor = (quantity_in_grams / base_serving) if base_serving > 0 else 0.0
    return {
        "calories": round(per_100g.get("calories", 0.0) * factor, 2),
        "protein": round(per_100g.get("protein", 0.0) * factor, 2),
        "carbs": round(per_100g.get("carbs", 0.0) * factor, 2),
        "fat": round(per_100g.get("fat", 0.0) * factor, 2),
        "fiber": round(per_100g.get("fiber", 0.0) * factor, 2),
        "sugar": round(per_100g.get("sugar", 0.0) * factor, 2),
    }


def _convert_with_allowed_units(
    quantity: float, unit: str, allowed_units: List[Dict[str, Any]],
    food_name: str = "",
) -> float:
    """Convert quantity to grams using food-specific allowed_units."""
    if unit.lower() == "g":
        return quantity

    for au in allowed_units:
        if au.get("unit", "").lower() == unit.lower():
            gram_weight = au.get("gram_weight", 1.0)
            return quantity * gram_weight

    # Fallback to global mapping if unit not in allowed_units
    logger.warning(
        f"Unit '{unit}' not in allowed_units, falling back to global mapping"
    )
    return convert_quantity_to_grams(quantity, unit, food_name)


def clamp_nutrition_values(item: dict) -> dict:
    """Clamp nutrition to physically plausible ranges for the given quantity.

    Macronutrients (protein/carbs/fat) cannot exceed the food's total weight.
    Returns clamped values; logs a warning when clamping occurs.
    """
    quantity = item.get("quantity", 1.0)
    unit = (item.get("unit") or "g").lower()

    # Estimate weight in grams for plausibility check
    food_name = item.get("name", "")
    weight_g = convert_quantity_to_grams(quantity, unit, food_name)
    if weight_g <= 0:
        return item

    calories = item.get("calories", 0.0)
    protein = item.get("protein", 0.0)
    carbs = item.get("carbs", 0.0)
    fat = item.get("fat", 0.0)

    # Each macro can't exceed total weight; calories max ~9 kcal/g (pure fat)
    max_cal = weight_g * 9.0
    clamped = {
        "calories": min(max(calories, 0), max_cal),
        "protein": min(max(protein, 0), weight_g),
        "carbs": min(max(carbs, 0), weight_g),
        "fat": min(max(fat, 0), weight_g),
    }

    if clamped != {"calories": calories, "protein": protein, "carbs": carbs, "fat": fat}:
        logger.warning(
            f"Clamped implausible nutrition for '{item.get('name', '?')}' "
            f"({quantity} {unit}): {calories:.1f}cal/{protein:.1f}p/{carbs:.1f}c/{fat:.1f}f "
            f"-> {clamped['calories']:.1f}cal/{clamped['protein']:.1f}p/"
            f"{clamped['carbs']:.1f}c/{clamped['fat']:.1f}f"
        )

    return clamped


@dataclass
class ScaledNutritionResult:
    """Result of nutrition calculation for a specific quantity."""
    calories: float
    protein: float
    carbs: float
    fat: float


class NutritionCalculationService:
    """
    Domain service for calculating nutrition from various sources.

    Provides a single source of truth for nutrition calculations, with
    fallback mechanisms for robustness.
    """

    def __init__(self, pinecone_service=None):
        """
        Initialize with optional services.

        Args:
            pinecone_service: Pinecone vector search service for ingredient lookup
        """
        self.pinecone_service = pinecone_service

    def get_nutrition_for_ingredient(
        self,
        name: str,
        quantity: float,
        unit: str,
        fdc_id: Optional[int] = None
    ) -> Optional[ScaledNutritionResult]:
        """
        Get nutrition data for an ingredient from any available source.

        Priority:
        1. Pinecone vector search (semantic matching)
        2. None if no source available

        Args:
            name: Ingredient name
            quantity: Amount of ingredient
            unit: Unit of measurement
            fdc_id: Optional food ID (kept for backward compat)

        Returns:
            ScaledNutritionResult or None if not found
        """
        # Priority 1: Pinecone semantic search
        if self.pinecone_service:
            try:
                result = self._get_from_pinecone(name, quantity, unit)
                if result:
                    logger.info(f"Got nutrition for '{name}' from Pinecone")
                    return result
            except Exception as e:
                logger.warning(f"Pinecone lookup failed for '{name}': {e}")

        logger.warning(f"Could not find nutrition data for '{name}'")
        return None

    def _get_from_pinecone(
        self,
        name: str,
        quantity: float,
        unit: str
    ) -> Optional[ScaledNutritionResult]:
        """Get nutrition from Pinecone service."""
        if not self.pinecone_service:
            return None

        scaled_nutrition = self.pinecone_service.get_scaled_nutrition(
            ingredient_name=name,
            quantity=quantity,
            unit=unit
        )

        if scaled_nutrition:
            return ScaledNutritionResult(
                calories=scaled_nutrition.calories,
                protein=scaled_nutrition.protein,
                carbs=scaled_nutrition.carbs,
                fat=scaled_nutrition.fat
            )

        return None


    def calculate_meal_total(self, food_items: List[FoodItem]) -> Nutrition:
        """
        Calculate total nutrition from a list of food items.

        Args:
            food_items: List of food items in the meal

        Returns:
            Nutrition object with totals
        """
        if not food_items:
            return Nutrition(
                macros=Macros(protein=0, carbs=0, fat=0),
                food_items=[],
                confidence_score=1.0
            )

        total_protein = sum(item.macros.protein for item in food_items)
        total_carbs = sum(item.macros.carbs for item in food_items)
        total_fat = sum(item.macros.fat for item in food_items)
        total_fiber = sum(item.macros.fiber for item in food_items)
        total_sugar = sum(item.macros.sugar for item in food_items)

        # Calculate average confidence
        avg_confidence = sum(item.confidence for item in food_items) / len(food_items)

        return Nutrition(
            macros=Macros(
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat,
                fiber=total_fiber,
                sugar=total_sugar,
            ),
            food_items=food_items,
            confidence_score=avg_confidence
        )

    def scale_nutrition(
        self,
        original_nutrition: ScaledNutritionResult,
        original_quantity: float,
        new_quantity: float
    ) -> ScaledNutritionResult:
        """
        Scale nutrition proportionally based on quantity change.

        Args:
            original_nutrition: Original nutrition values
            original_quantity: Original quantity
            new_quantity: New quantity

        Returns:
            Scaled nutrition values
        """
        if original_quantity <= 0:
            raise ValueError(f"Original quantity must be positive: {original_quantity}")

        scale_factor = new_quantity / original_quantity

        return ScaledNutritionResult(
            calories=original_nutrition.calories * scale_factor,
            protein=original_nutrition.protein * scale_factor,
            carbs=original_nutrition.carbs * scale_factor,
            fat=original_nutrition.fat * scale_factor
        )
