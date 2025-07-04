import logging
from dataclasses import dataclass
from typing import Optional

from src.domain.model.meal import Meal
from src.domain.model.meal_image import MealImage
from src.domain.ports.image_store_port import ImageStorePort
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.parsers.gpt_response_parser import GPTResponseParser, GPTResponseParsingError

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
    
    def handle_immediate(self, image_bytes: bytes, content_type: str) -> 'Meal':
        """
        Handle the upload of a meal image with immediate analysis.
        
        This method performs synchronous analysis and returns the complete meal
        with nutrition data immediately instead of using background processing.
        
        Args:
            image_bytes: The raw image bytes
            content_type: The MIME content type (image/jpeg or image/png)
            
        Returns:
            Meal with complete nutrition data
            
        Raises:
            RuntimeError: If analysis fails
        """
        # Save image to storage service
        image_id = self.image_store.save(image_bytes, content_type)
        
        # Determine image format and size
        image_format = "jpeg" if content_type in ["image/jpeg", "image/jpg"] else "png"
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
        
        # Persist the initial meal entity
        saved_meal = self.meal_repository.save(meal)
        
        try:
            # Mark as ANALYZING
            analyzing_meal = saved_meal.mark_analyzing()
            self.meal_repository.save(analyzing_meal)
            
            # Check if vision service is available
            if not self.vision_service:
                logger.error("Vision service not available for immediate analysis")
                failed_meal = analyzing_meal.mark_failed("Vision service not available")
                self.meal_repository.save(failed_meal)
                return failed_meal
            
            # Check if GPT parser is available
            if not self.gpt_parser:
                logger.error("GPT parser not available for immediate analysis")
                failed_meal = analyzing_meal.mark_failed("GPT parser not available")
                self.meal_repository.save(failed_meal)
                return failed_meal
            
            # Call Vision AI API for immediate analysis
            logger.info(f"Performing immediate analysis for meal {saved_meal.meal_id}")
            gpt_response = self.vision_service.analyze(image_bytes)
            
            # Parse the GPT response
            try:
                # Parse the dish name
                dish_name = self.gpt_parser.parse_dish_name(gpt_response)

                # Parse the GPT response
                nutrition = self.gpt_parser.parse_to_nutrition(gpt_response)
                
                # Extract raw JSON for storage
                raw_gpt_json = self.gpt_parser.extract_raw_json(gpt_response)
                
                # Update meal with nutrition data and dish name
                # First mark as READY with the nutrition data
                ready_meal = analyzing_meal.mark_ready(nutrition, dish_name)
                
                # Move to ENRICHING state (which keeps the nutrition data)
                enriched_meal = ready_meal.mark_enriching(raw_gpt_json)
                final_meal = self.meal_repository.save(enriched_meal)
                
                logger.info(f"Immediate analysis completed successfully for meal {saved_meal.meal_id}")
                return final_meal
                
            except GPTResponseParsingError as e:
                logger.error(f"Failed to parse GPT response for immediate analysis: {str(e)}")
                failed_meal = analyzing_meal.mark_failed(f"Failed to parse AI response: {str(e)}")
                self.meal_repository.save(failed_meal)
                return failed_meal
                
        except Exception as e:
            logger.error(f"Error during immediate analysis: {str(e)}", exc_info=True)
            try:
                # Try to mark meal as failed
                meal = self.meal_repository.find_by_id(saved_meal.meal_id)
                if meal:
                    failed_meal = meal.mark_failed(f"Immediate analysis error: {str(e)}")
                    self.meal_repository.save(failed_meal)
                    return failed_meal
                else:
                    # If we can't find the meal, create a failed one
                    failed_meal = saved_meal.mark_failed(f"Immediate analysis error: {str(e)}")
                    self.meal_repository.save(failed_meal)
                    return failed_meal
            except Exception as mark_failed_error:
                logger.error(f"Error marking meal as failed: {str(mark_failed_error)}")
                # Return the original meal with failed status
                failed_meal = saved_meal.mark_failed(f"Immediate analysis error: {str(e)}")
                return failed_meal
    
    def analyze_meal_background(self, meal_id: str) -> None:
        """
        Analyze a meal image in the background.
        
        This method is meant to be called as a FastAPI background task.
        
        Args:
            meal_id: The ID of the meal to analyze
        """
        self._analyze_meal_background_with_context(meal_id)
    
    def analyze_meal_with_portion_background(self, meal_id: str, portion_size: float, unit: str) -> None:
        """
        Re-analyze a meal with specific portion size context.
        
        Args:
            meal_id: The ID of the meal to analyze
            portion_size: The target portion size
            unit: The unit of the portion size
        """
        context = {
            "type": "portion",
            "portion_size": portion_size,
            "unit": unit
        }
        self._analyze_meal_background_with_context(meal_id, context)
    
    def analyze_meal_with_ingredients_background(self, meal_id: str, ingredients: list) -> None:
        """
        Re-analyze a meal with known ingredients context.
        
        Args:
            meal_id: The ID of the meal to analyze
            ingredients: List of ingredient dictionaries
        """
        context = {
            "type": "ingredients",
            "ingredients": ingredients
        }
        self._analyze_meal_background_with_context(meal_id, context)
    
    def analyze_meal_with_weight_background(self, meal_id: str, weight_grams: float) -> None:
        """
        Re-analyze a meal with specific weight context for accurate nutrition.
        
        This method calls the LLM to provide more accurate nutrition data
        based on the specified weight, rather than simple proportional scaling.
        
        Args:
            meal_id: The ID of the meal to analyze
            weight_grams: The target weight in grams
        """
        context = {
            "type": "weight",
            "weight_grams": weight_grams
        }
        self._analyze_meal_background_with_context(meal_id, context)
    
    def _analyze_meal_background_with_context(self, meal_id: str, context: dict = None) -> None:
        """
        Internal method to analyze a meal image with optional context.
        
        Args:
            meal_id: The ID of the meal to analyze
            context: Optional context for specialized analysis
        """
        try:
            logger.info(f"Background task: Processing meal {meal_id}" + (f" with {context['type']} context" if context else ""))
            
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
            
            # 3. Call Vision AI API with context
            if not self.vision_service:
                logger.error("Background task: Vision service not available")
                failed_meal = analyzing_meal.mark_failed("Vision service not available")
                self.meal_repository.save(failed_meal)
                return
            
            # Choose the appropriate analysis method based on context
            if context and context["type"] == "portion":
                logger.info(f"Analyzing with portion context: {context['portion_size']} {context['unit']}")
                gpt_response = self.vision_service.analyze_with_portion_context(
                    image_bytes, 
                    context["portion_size"], 
                    context["unit"]
                )
            elif context and context["type"] == "ingredients":
                logger.info(f"Analyzing with ingredients context: {len(context['ingredients'])} ingredients")
                gpt_response = self.vision_service.analyze_with_ingredients_context(
                    image_bytes, 
                    context["ingredients"]
                )
            elif context and context["type"] == "weight":
                logger.info(f"Analyzing with weight context: {context['weight_grams']} grams")
                gpt_response = self.vision_service.analyze_with_weight_context(
                    image_bytes, 
                    context["weight_grams"]
                )
            else:
                logger.info("Analyzing without additional context")
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
                
                context_info = f" with {context['type']} context" if context else ""
                logger.info(f"Background task: Successfully processed meal {meal_id}{context_info}")
                
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