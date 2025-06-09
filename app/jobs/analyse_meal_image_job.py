import logging
import time

from domain.model.meal import Meal, MealStatus
from domain.ports.image_store_port import ImageStorePort
from domain.ports.meal_repository_port import MealRepositoryPort
from domain.ports.vision_ai_service_port import VisionAIServicePort
from domain.services.gpt_response_parser import GPTResponseParser, GPTResponseParsingError
from infra.adapters.cloudinary_image_store import CloudinaryImageStore
from infra.adapters.image_store import ImageStore
from infra.adapters.vision_ai_service import VisionAIService
from infra.repositories.meal_repository import MealRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyseMealImageJob:
    """
    Background job to analyze meal images using OpenAI Vision.
    
    This class implements US-2.1 and US-2.2 - Load image, call OpenAI Vision,
    parse response, and update meal status.
    """
    
    def __init__(
        self,
        meal_repository: MealRepositoryPort = None,
        image_store: ImageStorePort = None,
        vision_service: VisionAIServicePort = None,
        gpt_parser: GPTResponseParser = None,
        batch_size: int = 5
    ):
        """
        Initialize the job with dependencies.
        
        Args:
            meal_repository: Repository for meal data
            image_store: Service for loading images
            vision_service: Service for AI vision analysis
            gpt_parser: Service for parsing GPT responses
            batch_size: Number of meals to process in one batch
        """
        self.meal_repository = meal_repository or MealRepository()
        
        # Use CloudinaryImageStore if USE_MOCK_STORAGE is 0
        import os
        use_mock = bool(int(os.getenv("USE_MOCK_STORAGE", "1")))
        if use_mock:
            self.image_store = image_store or ImageStore()
        else:
            self.image_store = image_store or CloudinaryImageStore()
            
        logger.info(f"Using image store: {self.image_store.__class__.__name__}")
        
        self.vision_service = vision_service or VisionAIService()
        self.gpt_parser = gpt_parser or GPTResponseParser()
        self.batch_size = batch_size
    
    def run(self) -> int:
        """
        Run the job to process meals in PROCESSING status.
        
        Returns:
            Number of meals processed
        """
        # Find meals in PROCESSING status
        meals_to_process = self.meal_repository.find_by_status(
            status=MealStatus.PROCESSING,
            limit=self.batch_size
        )
        
        if not meals_to_process:
            logger.info("No meals to process")
            return 0
        
        logger.info(f"Found {len(meals_to_process)} meals to process")
        
        processed_count = 0
        for meal in meals_to_process:
            try:
                self._process_meal(meal)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing meal {meal.meal_id}: {str(e)}")
                # Mark meal as failed
                failed_meal = meal.mark_failed(f"Processing error: {str(e)}")
                self.meal_repository.save(failed_meal)
        
        return processed_count
    
    def _process_meal(self, meal: Meal) -> None:
        """
        Process a single meal.
        
        Args:
            meal: The meal to process
        """
        logger.info(f"Processing meal {meal.meal_id}")
        logger.info(f"Image ID: {meal.image.image_id}, URL: {meal.image.url}")
        
        # 1. Mark as ANALYZING
        analyzing_meal = meal.mark_analyzing()
        self.meal_repository.save(analyzing_meal)
        
        # 2. Load image bytes
        logger.info(f"Attempting to load image {meal.image.image_id}")
        image_bytes = self.image_store.load(meal.image.image_id)
        if not image_bytes:
            logger.error(f"Could not load image {meal.image.image_id}")
            raise ValueError(f"Could not load image {meal.image.image_id}")
        
        logger.info(f"Successfully loaded image, size: {len(image_bytes)} bytes")
        
        # 3. Call OpenAI Vision API
        logger.info(f"Calling vision service to analyze image")
        gpt_response = self.vision_service.analyze(image_bytes)
        
        try:
            # 4. Parse the GPT response
            logger.info(f"Parsing GPT response")
            nutrition = self.gpt_parser.parse_to_nutrition(gpt_response)
            
            # 5. Extract raw JSON for storage
            raw_gpt_json = self.gpt_parser.extract_raw_json(gpt_response)
            
            # 6. Update meal with nutrition data
            # First mark as READY with the nutrition data
            ready_meal = analyzing_meal.mark_ready(nutrition)
            
            # 7. Move to ENRICHING state (which keeps the nutrition data)
            enriched_meal = ready_meal.mark_enriching(raw_gpt_json)
            self.meal_repository.save(enriched_meal)
            
            logger.info(f"Successfully processed meal {meal.meal_id}")
            
        except GPTResponseParsingError as e:
            logger.error(f"Failed to parse GPT response for meal {meal.meal_id}: {str(e)}")
            failed_meal = analyzing_meal.mark_failed(f"Failed to parse AI response: {str(e)}")
            self.meal_repository.save(failed_meal)


def run_job():
    """Run the job once."""
    job = AnalyseMealImageJob()
    processed = job.run()
    return processed


def run_continuous(interval_seconds: int = 10):
    """
    Run the job continuously with a specified interval.
    
    Args:
        interval_seconds: Seconds to wait between job runs
    """
    logger.info(f"Starting continuous job with {interval_seconds}s interval")
    job = AnalyseMealImageJob()
    
    try:
        while True:
            processed = job.run()
            logger.info(f"Processed {processed} meals")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info("Job stopped by user")


if __name__ == "__main__":
    # When run as a script, run continuously
    run_continuous() 