"""
Handler for ingredient recognition command.
"""

import base64
import binascii
import logging
from typing import Any, cast

from src.app.commands.ingredient import RecognizeIngredientCommand
from src.app.events.base import EventHandler, handles
from src.app.services.food_name_localizer import translate_food_texts
from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.domain.model.translation_result import TranslationOutcome
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024


@handles(RecognizeIngredientCommand)
class RecognizeIngredientCommandHandler(
    EventHandler[RecognizeIngredientCommand, dict[str, Any]]
):
    """Handler for recognizing ingredients from images."""

    def __init__(
        self,
        vision_service: VisionAIServicePort | None = None,
        translation_service: Any | None = None,
    ):
        self.vision_service = vision_service
        self.translation_service = translation_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.vision_service = kwargs.get("vision_service", self.vision_service)
        self.translation_service = kwargs.get(
            "translation_service", self.translation_service
        )

    async def handle(self, command: RecognizeIngredientCommand) -> dict[str, Any]:
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
                image_bytes = base64.b64decode(command.image_data, validate=True)
            except (binascii.Error, ValueError) as e:
                logger.warning(
                    "Failed to decode image data error_type=%s", type(e).__name__
                )
                return {
                    "name": None,
                    "confidence": 0.0,
                    "category": None,
                    "success": False,
                    "message": "Invalid image data format",
                }

            if len(image_bytes) > MAX_IMAGE_BYTES:
                return {
                    "name": None,
                    "confidence": 0.0,
                    "category": None,
                    "success": False,
                    "message": "Image too large (max 5MB)",
                }

            # Use the ingredient identification strategy
            strategy = (
                AnalysisStrategyFactory.create_ingredient_identification_strategy()
            )
            analyze = cast(Any, self.vision_service).analyze_with_strategy
            result = await analyze(image_bytes, strategy)

            # Parse structured_data from response
            data = result.get("structured_data", {})
            name = data.get("name")
            confidence = data.get("confidence", 0.0)
            category = data.get("category")

            # Determine success
            success = name is not None and confidence > 0.3

            logger.info(
                "Ingredient recognition completed confidence=%.2f name_present=%s "
                "category_present=%s",
                confidence,
                bool(name),
                bool(category),
            )

            # Translate ingredient name if non-English
            if (
                success
                and name
                and command.language != "en"
                and self.translation_service
            ):
                result = await translate_food_texts(
                    [str(name)],
                    target_language=command.language,
                    translation_service=self.translation_service,
                )
                if (
                    result.outcome
                    in {
                        TranslationOutcome.TRANSLATED,
                        TranslationOutcome.PARTIAL,
                    }
                    and result.texts
                ):
                    name = result.texts[0]

            return {
                "name": name,
                "confidence": confidence,
                "category": category,
                "success": success,
                "message": None if success else "Could not identify ingredient",
            }

        except AIUnavailableError:
            raise
        except Exception as e:
            logger.error(
                "Ingredient recognition failed error_type=%s", type(e).__name__
            )
            return {
                "name": None,
                "confidence": 0.0,
                "category": None,
                "success": False,
                "message": "Recognition failed",
            }
