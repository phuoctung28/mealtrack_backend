import logging
from dataclasses import dataclass
from typing import List, Optional, Dict

from src.domain.model.macros import Macros
from src.domain.model.nutrition import Nutrition, FoodItem
from src.domain.ports.food_database_port import FoodDatabasePort

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class EnrichmentResult:
    """Result of nutrition enrichment process."""
    nutrition: Nutrition
    enriched_items: int
    failed_lookups: List[str]

class NutritionService:
    """
    Domain service for nutrition enrichment and calculation.
    
    Implements US-3.2 - Recalculate totals and confidence after enrichment.
    """
    
    def __init__(self, food_database: FoodDatabasePort):
        """Initialize with food database dependency."""
        self.food_database = food_database
    
    def merge(self, ai_nutrition: Nutrition, database_lookups: Dict[str, Optional[FoodItem]]) -> Nutrition:
        """
        Merge AI-generated nutrition with database lookup results.
        
        Args:
            ai_nutrition: Original nutrition data from AI
            database_lookups: Dictionary mapping food names to database lookup results
            
        Returns:
            Enhanced Nutrition object with merged data and updated confidence
        """
        logger.info("Starting nutrition merge process")
        
        if not ai_nutrition.food_items:
            logger.warning("No food items in AI nutrition data")
            return ai_nutrition
        
        enriched_items = []
        total_confidence_weight = 0.0
        total_weight = 0.0
        
        # Process each food item
        for ai_item in ai_nutrition.food_items:
            db_item = database_lookups.get(ai_item.name)
            
            if db_item:
                # Use database data with high confidence
                enriched_item = db_item
                logger.info(f"Enhanced {ai_item.name} with database data")
            else:
                # Keep AI data but reduce confidence
                enriched_item = FoodItem(
                    name=ai_item.name,
                    quantity=ai_item.quantity,
                    unit=ai_item.unit,
                    calories=ai_item.calories,
                    macros=ai_item.macros,
                    micros=ai_item.micros,
                    confidence=min(ai_item.confidence, 0.4)  # Reduce confidence for failed lookups
                )
                logger.info(f"Kept AI data for {ai_item.name} (no database match)")
            
            enriched_items.append(enriched_item)
            
            # Calculate weighted confidence
            item_weight = enriched_item.calories if enriched_item.calories > 0 else 1.0
            total_confidence_weight += enriched_item.confidence * item_weight
            total_weight += item_weight
        
        # Calculate new totals
        total_calories = self._calculate_total_calories(enriched_items)
        total_macros = self._calculate_total_macros(enriched_items)
        
        # Calculate overall confidence score
        overall_confidence = total_confidence_weight / total_weight if total_weight > 0 else 0.5
        overall_confidence = round(overall_confidence, 2)
        
        # Create enhanced nutrition object
        enhanced_nutrition = Nutrition(
            calories=total_calories,
            macros=total_macros,
            micros=ai_nutrition.micros,  # Keep original micros for now
            food_items=enriched_items,
            confidence_score=overall_confidence
        )
        
        logger.info(f"Merge complete: {len(enriched_items)} items, confidence: {overall_confidence}")
        return enhanced_nutrition
    
    def enrich_nutrition(self, ai_nutrition: Nutrition) -> EnrichmentResult:
        """
        Enrich AI nutrition data with database lookups.
        
        Args:
            ai_nutrition: Original nutrition data from AI
            
        Returns:
            EnrichmentResult with enhanced nutrition and enrichment statistics
        """
        logger.info("Starting nutrition enrichment")
        
        if not ai_nutrition.food_items:
            logger.warning("No food items to enrich")
            return EnrichmentResult(
                nutrition=ai_nutrition,
                enriched_items=0,
                failed_lookups=[]
            )
        
        # Prepare batch lookup data
        lookup_items = []
        for item in ai_nutrition.food_items:
            lookup_items.append({
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit
            })
        
        # Perform batch lookup
        database_results = self.food_database.lookup_batch(lookup_items)
        
        # Count enrichment statistics
        enriched_count = sum(1 for result in database_results.values() if result is not None)
        failed_lookups = [name for name, result in database_results.items() if result is None]
        
        # Merge AI and database data
        enhanced_nutrition = self.merge(ai_nutrition, database_results)
        
        result = EnrichmentResult(
            nutrition=enhanced_nutrition,
            enriched_items=enriched_count,
            failed_lookups=failed_lookups
        )
        
        logger.info(f"Enrichment complete: {enriched_count}/{len(ai_nutrition.food_items)} items enriched")
        return result
    
    def _calculate_total_calories(self, food_items: List[FoodItem]) -> float:
        """Calculate total calories from food items."""
        total = sum(item.calories for item in food_items)
        return round(total, 1)  # Round to ±1 kcal as per acceptance criteria
    
    def _calculate_total_macros(self, food_items: List[FoodItem]) -> Macros:
        """Calculate total macros from food items."""
        total_protein = sum(item.macros.protein for item in food_items)
        total_carbs = sum(item.macros.carbs for item in food_items)
        total_fat = sum(item.macros.fat for item in food_items)
        
        # Calculate total fiber, handling None values
        fibers = [item.macros.fiber for item in food_items if item.macros.fiber is not None]
        total_fiber = sum(fibers) if fibers else None
        
        return Macros(
            protein=round(total_protein, 1),
            carbs=round(total_carbs, 1),
            fat=round(total_fat, 1),
            fiber=round(total_fiber, 1) if total_fiber is not None else None
        )
    
    def validate_nutrition_totals(self, nutrition: Nutrition) -> bool:
        """
        Validate that nutrition totals are consistent.
        
        Args:
            nutrition: Nutrition object to validate
            
        Returns:
            True if totals are consistent within ±1 kcal tolerance
        """
        if not nutrition.food_items:
            return True
        
        # Calculate expected totals from food items
        expected_calories = self._calculate_total_calories(nutrition.food_items)
        expected_macros = self._calculate_total_macros(nutrition.food_items)
        
        # Check calorie consistency (±1 kcal tolerance)
        calorie_diff = abs(nutrition.calories - expected_calories)
        if calorie_diff > 1.0:
            logger.warning(f"Calorie mismatch: {nutrition.calories} vs {expected_calories}")
            return False
        
        # Check macro consistency (±0.1g tolerance)
        macro_tolerance = 0.1
        
        if abs(nutrition.macros.protein - expected_macros.protein) > macro_tolerance:
            logger.warning(f"Protein mismatch: {nutrition.macros.protein} vs {expected_macros.protein}")
            return False
            
        if abs(nutrition.macros.carbs - expected_macros.carbs) > macro_tolerance:
            logger.warning(f"Carbs mismatch: {nutrition.macros.carbs} vs {expected_macros.carbs}")
            return False
            
        if abs(nutrition.macros.fat - expected_macros.fat) > macro_tolerance:
            logger.warning(f"Fat mismatch: {nutrition.macros.fat} vs {expected_macros.fat}")
            return False
        
        return True 