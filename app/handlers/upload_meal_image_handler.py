from dataclasses import dataclass
from typing import Dict, Any, Optional
from domain.model.meal import Meal, MealStatus
from domain.model.meal_image import MealImage
from domain.ports.image_store_port import ImageStorePort
from domain.ports.meal_repository_port import MealRepositoryPort
from domain.ports.vision_ai_service_port import VisionAIServicePort
from domain.services.gpt_response_parser import GPTResponseParser, GPTResponseParsingError
import logging

logger = logging.getLogger(__name__)

@dataclass
class UploadResult:
    """Result from uploading a meal image."""
    meal_id: str
    status: str


class UploadMealImageHandler:
    """
    Handler for uploading meal images.
    
    Implements US-1.3 and US-1.4 - Save the raw image bytes and persist initial Meal.
    """
    
    def __init__(
        self,
        image_store: ImageStorePort,
        meal_repository: MealRepositoryPort,
        vision_service: Optional[VisionAIServicePort] = None,
        gpt_parser: Optional[GPTResponseParser] = None
    ):
        self.image_store = image_store
        self.meal_repository = meal_repository
        self.vision_service = vision_service
        self.gpt_parser = gpt_parser
    
    def handle(self, image_bytes: bytes, content_type: str) -> UploadResult:
        """
        Handle the upload of a meal image.
        
        Args:
            image_bytes: The raw image bytes
            content_type: The MIME content type (image/jpeg or image/png)
            
        Returns:
            UploadResult with meal_id and status
        """
        # Save image to storage service
        image_id = self.image_store.save(image_bytes, content_type)
        
        # Determine image format and size
        image_format = "jpeg" if content_type == "image/jpeg" else "png"
        size_bytes = len(image_bytes)
        
        # Create MealImage value object
        meal_image = MealImage(
            image_id=image_id,
            format=image_format,
            size_bytes=size_bytes,
            url=self.image_store.get_url(image_id)
        )
        
        # Create Meal with PROCESSING status
        meal = Meal.create_new_processing(meal_image)
        
        # Persist the meal entity
        saved_meal = self.meal_repository.save(meal)
        
        return UploadResult(
            meal_id=saved_meal.meal_id,
            status=str(saved_meal.status)
        )
    
    def analyze_meal_background(self, meal_id: str) -> None:
        """
        Analyze a meal image in the background.
        
        This method is meant to be called as a FastAPI background task.
        
        Args:
            meal_id: The ID of the meal to analyze
        """
        try:
            logger.info(f"Background task: Processing meal {meal_id}")
            
            # Fetch the meal from the repository
            meal = self.meal_repository.find_by_id(meal_id)
            if not meal:
                logger.error(f"Background task: Meal {meal_id} not found")
                return
            
            # 1. Mark as ANALYZING
            analyzing_meal = meal.mark_analyzing()
            self.meal_repository.save(analyzing_meal)
            
            # 2. Load the image
            image_id = meal.image.image_id
            image_bytes = self.image_store.load(image_id)
            
            if not image_bytes:
                logger.error(f"Background task: Failed to load image {image_id}")
                failed_meal = analyzing_meal.mark_failed("Failed to load image")
                self.meal_repository.save(failed_meal)
                return
            
            # 3. Call Vision AI API
            if not self.vision_service:
                logger.error("Background task: Vision service not available")
                failed_meal = analyzing_meal.mark_failed("Vision service not available")
                self.meal_repository.save(failed_meal)
                return
                
            gpt_response = self.vision_service.analyze(image_bytes)
            
            # 4. Parse the GPT response
            if not self.gpt_parser:
                logger.error("Background task: GPT parser not available")
                failed_meal = analyzing_meal.mark_failed("GPT parser not available")
                self.meal_repository.save(failed_meal)
                return
                
            try:
                # Parse the GPT response
                nutrition = self.gpt_parser.parse_to_nutrition(gpt_response)
                
                # Extract raw JSON for storage
                raw_gpt_json = self.gpt_parser.extract_raw_json(gpt_response)
                
                # Update meal with nutrition data
                # First mark as READY with the nutrition data
                ready_meal = analyzing_meal.mark_ready(nutrition)
                
                # Move to ENRICHING state (which keeps the nutrition data)
                enriched_meal = ready_meal.mark_enriching(raw_gpt_json)
                self.meal_repository.save(enriched_meal)
                
                logger.info(f"Background task: Successfully processed meal {meal_id}")
                
            except GPTResponseParsingError as e:
                logger.error(f"Background task: Failed to parse GPT response for meal {meal_id}: {str(e)}")
                failed_meal = analyzing_meal.mark_failed(f"Failed to parse AI response: {str(e)}")
                self.meal_repository.save(failed_meal)
                
        except Exception as e:
            logger.error(f"Background task: Error processing meal {meal_id}: {str(e)}", exc_info=True)
            try:
                # Try to mark meal as failed
                meal = self.meal_repository.find_by_id(meal_id)
                if meal:
                    failed_meal = meal.mark_failed(f"Processing error: {str(e)}")
                    self.meal_repository.save(failed_meal)
            except Exception as mark_failed_error:
                logger.error(f"Background task: Error marking meal as failed: {str(mark_failed_error)}") 