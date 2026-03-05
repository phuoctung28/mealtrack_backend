"""
Nutrition calculation service - domain service for nutrition-related operations.
Provides a unified interface for calculating nutrition from various sources.
"""
import logging
from dataclasses import dataclass
from typing import Optional, List

from src.domain.model.nutrition import FoodItem, Nutrition
from src.domain.model.nutrition import Macros

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


def convert_quantity_to_grams(quantity: float, unit: str) -> float:
    """Convert a quantity+unit pair to grams using UNIT_TO_GRAMS mapping."""
    normalized = _normalize_unit(unit)
    if normalized == "g":
        return quantity
    grams_per_unit = UNIT_TO_GRAMS.get(normalized)
    if grams_per_unit is None:
        logger.warning(f"Unknown unit '{unit}' (normalized: '{normalized}') — treating quantity as grams")
        return quantity
    return quantity * grams_per_unit


def scale_per_100g_nutrition(
    per_100g: dict, quantity: float, unit: str, base_serving: float = 100.0
) -> dict:
    """Scale per-100g nutrition values for a given quantity and unit.

    Returns dict with keys: calories, protein, carbs, fat.
    """
    quantity_in_grams = convert_quantity_to_grams(quantity, unit)
    factor = (quantity_in_grams / base_serving) if base_serving > 0 else 0.0
    return {
        "calories": round(per_100g.get("calories", 0.0) * factor, 2),
        "protein": round(per_100g.get("protein", 0.0) * factor, 2),
        "carbs": round(per_100g.get("carbs", 0.0) * factor, 2),
        "fat": round(per_100g.get("fat", 0.0) * factor, 2),
    }


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
                calories=0,
                macros=Macros(protein=0, carbs=0, fat=0),
                food_items=[],
                confidence_score=1.0
            )

        total_calories = sum(item.calories for item in food_items)
        total_protein = sum(item.macros.protein for item in food_items)
        total_carbs = sum(item.macros.carbs for item in food_items)
        total_fat = sum(item.macros.fat for item in food_items)

        # Calculate average confidence
        avg_confidence = sum(item.confidence for item in food_items) / len(food_items)

        return Nutrition(
            calories=total_calories,
            macros=Macros(
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat
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
