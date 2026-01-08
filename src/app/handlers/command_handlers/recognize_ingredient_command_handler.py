"""
Handler for ingredient recognition command.
"""
import base64
import logging
from typing import Dict, Any

from src.app.commands.ingredient import RecognizeIngredientCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory

logger = logging.getLogger(__name__)


@handles(RecognizeIngredientCommand)
class RecognizeIngredientCommandHandler(EventHandler[RecognizeIngredientCommand, Dict[str, Any]]):
    """Handler for recognizing ingredients from images."""

    def __init__(self, vision_service: VisionAIServicePort = None):
        self.vision_service = vision_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.vision_service = kwargs.get('vision_service', self.vision_service)

    async def handle(self, command: RecognizeIngredientCommand) -> Dict[str, Any]:
        """
        Handle ingredient recognition from image.

        Returns:
            Dictionary with:
            - name: Identified ingredient name (or None)
            - confidence: Confidence score (0-1)
            - category: Ingredient category
            - success: Whether recognition was successful
            - message: Optional error/info message
        """
        if not self.vision_service:
            raise RuntimeError("Vision service not configured")

        try:
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(command.image_data)
            except Exception as e:
                logger.warning(f"Failed to decode image data: {e}")
                return {
                    "name": None,
                    "confidence": 0.0,
                    "category": None,
                    "success": False,
                    "message": "Invalid image data format"
                }

            # Validate image size (max 5MB)
            max_size_bytes = 5 * 1024 * 1024
            if len(image_bytes) > max_size_bytes:
                return {
                    "name": None,
                    "confidence": 0.0,
                    "category": None,
                    "success": False,
                    "message": "Image too large (max 5MB)"
                }

            # Use the ingredient identification strategy
            strategy = AnalysisStrategyFactory.create_ingredient_identification_strategy()
            result = self.vision_service.analyze_with_strategy(image_bytes, strategy)

            # Parse structured_data from response
            data = result.get("structured_data", {})
            name = data.get("name")
            confidence = data.get("confidence", 0.0)
            category = data.get("category")

            # Determine success
            success = name is not None and confidence > 0.3

            logger.info(
                f"Ingredient recognition completed: name={name}, "
                f"confidence={confidence:.2f}, category={category}"
            )

            return {
                "name": name,
                "confidence": confidence,
                "category": category,
                "success": success,
                "message": None if success else "Could not identify ingredient"
            }

        except Exception as e:
            logger.error(f"Ingredient recognition failed: {e}")
            return {
                "name": None,
                "confidence": 0.0,
                "category": None,
                "success": False,
                "message": f"Recognition failed: {str(e)}"
            }
