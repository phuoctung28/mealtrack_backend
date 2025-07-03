import logging
from typing import Optional

from src.domain.model.meal import Meal, MealStatus
from src.domain.ports.food_database_port import FoodDatabasePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.services.gpt_response_parser import GPTResponseParser
from src.domain.services.nutrition_service import NutritionService

# Configure logging
logger = logging.getLogger(__name__)

class EnrichNutritionHandler:
    """
    Application handler for nutrition enrichment process.
    
    Implements US-3.3 - Update meal with final nutrition and mark status="READY".
    """
    
    def __init__(self, 
                 meal_repository: MealRepositoryPort,
                 food_database: FoodDatabasePort):
        """Initialize handler with dependencies."""
        self.meal_repository = meal_repository
        self.nutrition_service = NutritionService(food_database)
        self.gpt_parser = GPTResponseParser()
    
    def handle(self, meal_id: str, gpt_response: dict) -> Optional[Meal]:
        """
        Handle nutrition enrichment for a meal.
        
        Args:
            meal_id: ID of the meal to enrich
            gpt_response: Raw GPT response with meal analysis
            
        Returns:
            Updated meal with enriched nutrition, or None if failed
        """
        logger.info(f"Starting nutrition enrichment for meal {meal_id}")
        
        try:
            # Get the meal
            meal = self.meal_repository.get_by_id(meal_id)
            if not meal:
                logger.error(f"Meal not found: {meal_id}")
                return None
            
            # Check meal status
            if meal.status != MealStatus.ENRICHING:
                logger.warning(f"Meal {meal_id} is not in ENRICHING status: {meal.status}")
                return meal  # Return current state
            
            # Parse GPT response to get AI nutrition data
            ai_nutrition = self.gpt_parser.parse_to_nutrition(gpt_response)
            logger.info(f"Parsed AI nutrition: {len(ai_nutrition.food_items or [])} food items")
            
            # Enrich nutrition with database lookups
            enrichment_result = self.nutrition_service.enrich_nutrition(ai_nutrition)
            
            # Log enrichment statistics
            logger.info(f"Enrichment stats: {enrichment_result.enriched_items} enriched, "
                       f"{len(enrichment_result.failed_lookups)} failed")
            
            if enrichment_result.failed_lookups:
                logger.info(f"Failed lookups: {enrichment_result.failed_lookups}")
            
            # Validate final nutrition data
            if not self.nutrition_service.validate_nutrition_totals(enrichment_result.nutrition):
                logger.warning(f"Nutrition validation failed for meal {meal_id}")
                # Continue anyway - validation warnings are logged
            
            # Mark meal as ready with enriched nutrition
            enriched_meal = meal.mark_ready(enrichment_result.nutrition)
            
            # Save to repository
            saved_meal = self.meal_repository.save(enriched_meal)
            
            logger.info(f"Nutrition enrichment completed for meal {meal_id}")
            logger.info(f"Final nutrition - Calories: {enrichment_result.nutrition.calories}, "
                       f"Confidence: {enrichment_result.nutrition.confidence_score}")
            
            return saved_meal
            
        except Exception as e:
            logger.error(f"Error enriching nutrition for meal {meal_id}: {str(e)}")
            
            # Try to mark meal as failed
            try:
                if meal:
                    failed_meal = meal.mark_failed(f"Nutrition enrichment failed: {str(e)}")
                    self.meal_repository.save(failed_meal)
                    return failed_meal
            except Exception as save_error:
                logger.error(f"Failed to save error state for meal {meal_id}: {str(save_error)}")
            
            return None
    
    def handle_enrichment_job(self, meal_id: str) -> bool:
        """
        Handle enrichment as a background job.
        
        Args:
            meal_id: ID of the meal to enrich
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Running enrichment job for meal {meal_id}")
        
        try:
            # Get the meal
            meal = self.meal_repository.get_by_id(meal_id)
            if not meal:
                logger.error(f"Meal not found: {meal_id}")
                return False
            
            # Check if we have raw GPT response
            if not meal.raw_gpt_json:
                logger.error(f"No raw GPT response found for meal {meal_id}")
                return False
            
            # Parse the stored GPT response
            import json
            try:
                gpt_response = json.loads(meal.raw_gpt_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in raw GPT response for meal {meal_id}: {str(e)}")
                return False
            
            # Run enrichment
            result = self.handle(meal_id, gpt_response)
            return result is not None and result.status == MealStatus.READY
            
        except Exception as e:
            logger.error(f"Enrichment job failed for meal {meal_id}: {str(e)}")
            return False 