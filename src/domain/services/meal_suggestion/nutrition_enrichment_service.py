"""
Service to calculate nutrition from AI-generated ingredient lists.
Uses existing Pinecone nutrition data for accuracy.
"""
import logging
from typing import List
from dataclasses import dataclass

from src.domain.model.meal_suggestion.meal_suggestion import Ingredient, MacroEstimate
from src.infra.services.pinecone_service import PineconeNutritionService

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result of nutrition enrichment."""
    macros: MacroEstimate
    confidence_score: float
    missing_ingredients: List[str]


class NutritionEnrichmentService:
    """Calculates meal nutrition from ingredient lists using Pinecone."""

    def __init__(self, pinecone_service: PineconeNutritionService = None):
        """Initialize with optional Pinecone service."""
        self._pinecone = pinecone_service
        if not self._pinecone:
            try:
                self._pinecone = PineconeNutritionService()
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone service: {e}")
                self._pinecone = None

    def calculate_meal_nutrition(
        self,
        ingredients: List[Ingredient],
        target_calories: int
    ) -> EnrichmentResult:
        """
        Calculate total nutrition for a meal from ingredients.

        Args:
            ingredients: List of ingredients with amounts and units
            target_calories: Expected calories (for validation)

        Returns:
            EnrichmentResult with calculated macros and confidence
        """
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        found_count = 0
        missing = []

        if not ingredients:
            logger.warning("No ingredients provided for nutrition calculation")
            return self._create_fallback_result(target_calories)

        for ingredient in ingredients:
            if not self._pinecone:
                # No Pinecone service available, use estimation
                estimated = self._estimate_nutrition(ingredient, target_calories, len(ingredients))
                total_calories += estimated['calories']
                total_protein += estimated['protein']
                total_carbs += estimated['carbs']
                total_fat += estimated['fat']
                continue

            nutrition = self._pinecone.get_scaled_nutrition(
                ingredient_name=ingredient.name,
                quantity=ingredient.amount,
                unit=ingredient.unit
            )

            if nutrition:
                total_calories += nutrition.calories
                total_protein += nutrition.protein
                total_carbs += nutrition.carbs
                total_fat += nutrition.fat
                found_count += 1
                logger.debug(
                    f"Found nutrition for {ingredient.name}: "
                    f"{nutrition.calories:.0f} cal, {nutrition.protein:.1f}g protein"
                )
            else:
                missing.append(ingredient.name)
                # Use fallback estimation
                estimated = self._estimate_nutrition(ingredient, target_calories, len(ingredients))
                total_calories += estimated['calories']
                total_protein += estimated['protein']
                total_carbs += estimated['carbs']
                total_fat += estimated['fat']
                logger.debug(
                    f"Missing nutrition data for {ingredient.name}, using estimation: "
                    f"{estimated['calories']:.0f} cal"
                )

        # Calculate confidence (0.0-1.0)
        confidence = found_count / len(ingredients) if ingredients else 0.5

        # Validate against target (warn if >20% off)
        if target_calories > 0:
            deviation = abs(total_calories - target_calories) / target_calories
            if deviation > 0.2:
                logger.warning(
                    f"Calculated calories {total_calories:.0f} differs from target {target_calories} "
                    f"by {deviation*100:.1f}% (>20%)"
                )

        if missing:
            logger.info(
                f"Nutrition enrichment: {found_count}/{len(ingredients)} found, "
                f"{len(missing)} estimated, confidence={confidence:.2f}"
            )

        return EnrichmentResult(
            macros=MacroEstimate(
                calories=round(total_calories),
                protein=round(total_protein, 1),
                carbs=round(total_carbs, 1),
                fat=round(total_fat, 1)
            ),
            confidence_score=confidence,
            missing_ingredients=missing
        )

    def _convert_to_grams(self, quantity: float, unit: str) -> float:
        """
        Convert quantity in any unit to grams.
        
        Args:
            quantity: The amount to convert
            unit: The unit of measurement (case-insensitive)
            
        Returns:
            Quantity in grams
        """
        unit_lower = unit.lower().strip()
        
        # Unit conversion table to grams (approximate conversions)
        unit_conversions = {
            # Weight units
            'g': 1, 'gram': 1, 'grams': 1,
            'kg': 1000, 'kilogram': 1000, 'kilograms': 1000,
            'oz': 28.35, 'ounce': 28.35, 'ounces': 28.35,
            'lb': 453.59, 'pound': 453.59, 'pounds': 453.59,
            # Volume units (approximate, varies by ingredient)
            'cup': 240, 'cups': 240,
            'tbsp': 15, 'tablespoon': 15, 'tablespoons': 15, 'tbs': 15,
            'tsp': 5, 'teaspoon': 5, 'teaspoons': 5,
            'ml': 1, 'milliliter': 1, 'milliliters': 1,  # 1ml ≈ 1g for water-based
            'l': 1000, 'liter': 1000, 'liters': 1000, 'litre': 1000, 'litres': 1000,
            'fl oz': 30, 'fluid ounce': 30, 'fluid ounces': 30,
            # Count units (approximate serving sizes)
            'serving': 100, 'servings': 100,
            'piece': 50, 'pieces': 50,  # Average piece size
            'slice': 25, 'slices': 25,  # Average slice size
            'unit': 100, 'units': 100,
        }
        
        conversion_factor = unit_conversions.get(unit_lower, 1)
        return quantity * conversion_factor

    def _estimate_nutrition(self, ingredient: Ingredient, target_calories: int, ingredient_count: int) -> dict:
        """
        Fallback nutrition estimation for missing ingredients.
        Uses category-based heuristics.
        """
        name_lower = ingredient.name.lower()

        # Category-based estimation per 100g (or adjusted for amount)
        if any(word in name_lower for word in ["oil", "butter", "cream", "mayo", "mayonnaise"]):
            # High-fat items: ~9 cal/g
            cal_per_gram = 9.0
            protein_ratio = 0.01  # 1% protein
            carbs_ratio = 0.01    # 1% carbs
            fat_ratio = 0.98      # 98% fat
        elif any(word in name_lower for word in ["meat", "chicken", "fish", "beef", "pork", "turkey", "lamb", "salmon", "tuna"]):
            # Protein-rich: ~150 cal/100g
            cal_per_gram = 1.5
            protein_ratio = 0.50  # 50% from protein (4 cal/g)
            carbs_ratio = 0.0     # 0% carbs
            fat_ratio = 0.50      # 50% from fat (9 cal/g)
        elif any(word in name_lower for word in ["rice", "pasta", "bread", "flour", "oats", "quinoa", "noodles"]):
            # High-carb: ~350 cal/100g
            cal_per_gram = 3.5
            protein_ratio = 0.12  # 12% from protein
            carbs_ratio = 0.75    # 75% from carbs
            fat_ratio = 0.03      # 3% from fat
        elif any(word in name_lower for word in ["cheese", "milk", "yogurt", "cream cheese"]):
            # Dairy: ~250 cal/100g
            cal_per_gram = 2.5
            protein_ratio = 0.25  # 25% from protein
            carbs_ratio = 0.15    # 15% from carbs
            fat_ratio = 0.55      # 55% from fat
        elif any(word in name_lower for word in ["egg", "eggs"]):
            # Eggs: ~155 cal/100g
            cal_per_gram = 1.55
            protein_ratio = 0.36  # 36% from protein
            carbs_ratio = 0.04    # 4% from carbs
            fat_ratio = 0.60      # 60% from fat
        elif any(word in name_lower for word in ["nuts", "almonds", "walnuts", "peanuts", "cashews"]):
            # Nuts: ~600 cal/100g
            cal_per_gram = 6.0
            protein_ratio = 0.15  # 15% from protein
            carbs_ratio = 0.15    # 15% from carbs
            fat_ratio = 0.70      # 70% from fat
        else:
            # Vegetables/default: ~50 cal/100g
            cal_per_gram = 0.5
            protein_ratio = 0.15  # 15% from protein
            carbs_ratio = 0.70    # 70% from carbs
            fat_ratio = 0.05      # 5% from fat

        # Convert ingredient amount to grams before calculating calories
        amount_in_grams = self._convert_to_grams(ingredient.amount, ingredient.unit)
        
        # Calculate total calories based on amount in grams
        estimated_calories = amount_in_grams * cal_per_gram

        # Calculate macros (calories from each macro / calories per gram of that macro)
        estimated_protein = (estimated_calories * protein_ratio) / 4  # 4 cal/g protein
        estimated_carbs = (estimated_calories * carbs_ratio) / 4      # 4 cal/g carbs
        estimated_fat = (estimated_calories * fat_ratio) / 9          # 9 cal/g fat

        return {
            'calories': estimated_calories,
            'protein': estimated_protein,
            'carbs': estimated_carbs,
            'fat': estimated_fat
        }

    def _create_fallback_result(self, target_calories: int) -> EnrichmentResult:
        """Create fallback result when no ingredients are provided."""
        # Use typical macro split: 30% protein, 40% carbs, 30% fat
        return EnrichmentResult(
            macros=MacroEstimate(
                calories=target_calories,
                protein=round((target_calories * 0.30) / 4, 1),  # 30% from protein
                carbs=round((target_calories * 0.40) / 4, 1),    # 40% from carbs
                fat=round((target_calories * 0.30) / 9, 1)       # 30% from fat
            ),
            confidence_score=0.3,  # Low confidence for fallback
            missing_ingredients=[]
        )
