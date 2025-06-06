import logging
import time
from typing import List

from domain.model.meal import MealStatus
from domain.ports.meal_repository_port import MealRepositoryPort
from domain.ports.food_database_port import FoodDatabasePort
from app.handlers.enrich_nutrition_handler import EnrichNutritionHandler

from infra.repositories.meal_repository import MealRepository
from infra.adapters.usda_food_database import USDAFoodDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnrichNutritionJob:
    """
    Background job to enrich meal nutrition using food database lookups.
    
    This job implements Epic 3 - Nutrition Enrichment (Sprint 3).
    Processes meals in ENRICHING status and enhances their nutrition data.
    """
    
    def __init__(
        self,
        meal_repository: MealRepositoryPort = None,
        food_database: FoodDatabasePort = None,
        batch_size: int = 5
    ):
        """
        Initialize the job with dependencies.
        
        Args:
            meal_repository: Repository for meal data
            food_database: Service for food database lookups
            batch_size: Number of meals to process in one batch
        """
        self.meal_repository = meal_repository or MealRepository()
        self.food_database = food_database or USDAFoodDatabase()
        self.enrichment_handler = EnrichNutritionHandler(
            meal_repository=self.meal_repository,
            food_database=self.food_database
        )
        self.batch_size = batch_size
        
        logger.info(f"Initialized EnrichNutritionJob with {self.food_database.__class__.__name__}")
    
    def run(self) -> int:
        """
        Run the job to process meals in ENRICHING status.
        
        Returns:
            Number of meals processed
        """
        # Find meals in ENRICHING status
        meals_to_enrich = self.meal_repository.find_by_status(
            status=MealStatus.ENRICHING,
            limit=self.batch_size
        )
        
        if not meals_to_enrich:
            logger.info("No meals to enrich")
            return 0
        
        logger.info(f"Found {len(meals_to_enrich)} meals to enrich")
        
        processed_count = 0
        for meal in meals_to_enrich:
            try:
                success = self.enrichment_handler.handle_enrichment_job(meal.meal_id)
                if success:
                    processed_count += 1
                    logger.info(f"Successfully enriched meal {meal.meal_id}")
                else:
                    logger.warning(f"Failed to enrich meal {meal.meal_id}")
            except Exception as e:
                logger.error(f"Error enriching meal {meal.meal_id}: {str(e)}")
        
        logger.info(f"Enrichment batch complete: {processed_count}/{len(meals_to_enrich)} successful")
        return processed_count
    
    def process_single_meal(self, meal_id: str) -> bool:
        """
        Process a single meal by ID.
        
        Args:
            meal_id: ID of the meal to process
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing single meal: {meal_id}")
        
        try:
            success = self.enrichment_handler.handle_enrichment_job(meal_id)
            if success:
                logger.info(f"Successfully enriched meal {meal_id}")
            else:
                logger.warning(f"Failed to enrich meal {meal_id}")
            return success
        except Exception as e:
            logger.error(f"Error enriching meal {meal_id}: {str(e)}")
            return False


def run_job():
    """Run the enrichment job once."""
    job = EnrichNutritionJob()
    processed = job.run()
    return processed


def run_continuous(interval_seconds: int = 15):
    """
    Run the job continuously with a specified interval.
    
    Args:
        interval_seconds: Seconds to wait between job runs
    """
    logger.info(f"Starting continuous enrichment job with {interval_seconds}s interval")
    job = EnrichNutritionJob()
    
    try:
        while True:
            processed = job.run()
            if processed > 0:
                logger.info(f"Enriched {processed} meals")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info("Enrichment job stopped by user")


def process_meal(meal_id: str):
    """
    Process a specific meal by ID.
    
    Args:
        meal_id: ID of the meal to process
    """
    job = EnrichNutritionJob()
    return job.process_single_meal(meal_id)


if __name__ == "__main__":
    # When run as a script, run continuously
    run_continuous() 