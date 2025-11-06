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

    def __init__(self, pinecone_service=None, usda_service=None):
        """
        Initialize with optional services.

        Args:
            pinecone_service: Pinecone vector search service for ingredient lookup
            usda_service: USDA FoodData Central API service
        """
        self.pinecone_service = pinecone_service
        self.usda_service = usda_service

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
        1. USDA FoodData Central (if fdc_id provided)
        2. Pinecone vector search (semantic matching)
        3. None if no source available

        Args:
            name: Ingredient name
            quantity: Amount of ingredient
            unit: Unit of measurement
            fdc_id: Optional USDA FDC ID for direct lookup

        Returns:
            ScaledNutritionResult or None if not found
        """
        # Priority 1: USDA direct lookup if FDC ID provided
        if fdc_id and self.usda_service:
            try:
                result = self._get_from_usda(fdc_id, quantity, unit)
                if result:
                    logger.info(f"Got nutrition for '{name}' from USDA (fdc_id={fdc_id})")
                    return result
            except Exception as e:
                logger.warning(f"USDA lookup failed for fdc_id={fdc_id}: {e}")

        # Priority 2: Pinecone semantic search
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

    def _get_from_usda(
        self,
        fdc_id: int,
        quantity: float,
        unit: str
    ) -> Optional[ScaledNutritionResult]:
        """Get nutrition from USDA service."""
        if not self.usda_service:
            return None

        # USDA service would need to be implemented
        # For now, return None as placeholder
        logger.debug(f"USDA service not yet fully implemented for fdc_id={fdc_id}")
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
