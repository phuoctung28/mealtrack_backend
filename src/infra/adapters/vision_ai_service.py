import asyncio
import json
import logging
from io import BytesIO
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image

from src.domain.exceptions.ai_exceptions import (
    AIOutputValidationError,
    AIUnavailableError,
)
from src.domain.model.ai.nutrition_contracts import VisionNutritionResponse
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.ai_output_validation_service import (
    build_validation_retry_prompt,
    validate_ai_output,
)
from src.domain.strategies.meal_analysis_strategy import (
    AnalysisStrategyFactory,
    IngredientIdentificationStrategy,
    MealAnalysisStrategy,
)
from src.infra.ai.gemini_service import GeminiService
from src.infra.ai.json_extract import extract_json
from src.infra.ai.model_config import ModelPurpose
from src.infra.config.settings import get_settings

logger = logging.getLogger(__name__)

MAX_URL_IMAGE_BYTES = 5 * 1024 * 1024
URL_FETCH_TIMEOUT_SECONDS = 10
ALLOWED_URL_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
VISION_VALIDATION_PURPOSE = "meal_scan"
MAX_VALIDATION_ATTEMPTS = 2


class VisionAIService(VisionAIServicePort):
    """Vision AI service with automatic fallback on failures."""

    def __init__(self, max_output_tokens: int | None = None):
        """Initialize with AI model manager."""
        self._ai_manager = GeminiService.get_instance()
        self._optimized_prompt_enabled = True
        self._max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else get_settings().MEAL_ANALYZE_MAX_OUTPUT_TOKENS
        )

    def _compress_image(self, image_bytes: bytes) -> bytes:
        """Compress image for faster upload."""
        try:
            img: Image.Image = Image.open(BytesIO(image_bytes))
            w, h = img.size

            if (
                img.format == "JPEG"
                and max(w, h) <= 768
                and len(image_bytes) < 200 * 1024
            ):  # already small JPEG
                return image_bytes

            if max(w, h) > 768:
                ratio = 768 / max(w, h)
                img = img.resize(
                    (int(w * ratio), int(h * ratio)),
                    Image.Resampling.LANCZOS,
                )

            if img.mode != "RGB":
                img = img.convert("RGB")

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except Exception as exc:
            logger.warning("Image compression failed, using original: %s", exc)
            return image_bytes

    async def analyze_with_strategy(
        self, image_bytes: bytes, strategy: MealAnalysisStrategy
    ) -> dict[str, Any]:
        """
        Analyze a food image using the provided analysis strategy with automatic fallback.

        Args:
            image_bytes: The raw bytes of the image to analyze
            strategy: The analysis strategy to use

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
        """
        image_bytes = self._compress_image(image_bytes)

        if isinstance(strategy, IngredientIdentificationStrategy):
            return await self._analyze_without_nutrition_contract(image_bytes, strategy)

        base_prompt = strategy.get_user_message()
        prompt = base_prompt

        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            try:
                result = await self._ai_manager.vision(
                    purpose=ModelPurpose.MEAL_SCAN,
                    image_bytes=image_bytes,
                    prompt=prompt,
                    system_prompt=strategy.get_analysis_prompt(),
                    schema=VisionNutritionResponse,
                    max_tokens=self._max_output_tokens,
                )
                validated = validate_ai_output(
                    result,
                    schema=VisionNutritionResponse,
                    purpose=VISION_VALIDATION_PURPOSE,
                    attempt_count=attempt,
                )
                structured_data = self._to_legacy_vision_payload(validated)
                if attempt > 1:
                    logger.info(
                        "[AI-OUTPUT-VALIDATION-RETRY-SUCCESS] "
                        "purpose=%s strategy=%s attempt=%s",
                        VISION_VALIDATION_PURPOSE,
                        strategy.get_strategy_name(),
                        attempt,
                    )
                return {
                    "raw_response": json.dumps(structured_data),
                    "structured_data": structured_data,
                    "strategy_used": strategy.get_strategy_name(),
                }
            except AIOutputValidationError as exc:
                logger.warning(
                    "[AI-OUTPUT-VALIDATION-FAILED] purpose=%s strategy=%s attempt=%s "
                    "details=%s",
                    VISION_VALIDATION_PURPOSE,
                    strategy.get_strategy_name(),
                    attempt,
                    exc.validation_details,
                )
                if attempt >= MAX_VALIDATION_ATTEMPTS:
                    raise AIOutputValidationError(
                        "Invalid AI output after validation retry",
                        purpose=VISION_VALIDATION_PURPOSE,
                        attempt_count=attempt,
                        validation_details=exc.validation_details,
                    ) from exc
                prompt = build_validation_retry_prompt(base_prompt, exc)
            except AIUnavailableError:
                raise
            except Exception as e:
                raise RuntimeError(
                    f"Failed to analyze image with {strategy.get_strategy_name()}: {str(e)}"
                ) from e

        raise RuntimeError("Failed to analyze image after validation retry")

    async def _analyze_without_nutrition_contract(
        self, image_bytes: bytes, strategy: MealAnalysisStrategy
    ) -> dict[str, Any]:
        """Run non-nutrition vision strategies with their own response contract."""
        try:
            result = await self._ai_manager.vision(
                purpose=ModelPurpose.MEAL_SCAN,
                image_bytes=image_bytes,
                prompt=strategy.get_user_message(),
                system_prompt=strategy.get_analysis_prompt(),
                max_tokens=self._max_output_tokens,
            )
            structured_data = (
                result if isinstance(result, dict) else extract_json(str(result))
            )
            return {
                "raw_response": json.dumps(structured_data),
                "structured_data": structured_data,
                "strategy_used": strategy.get_strategy_name(),
            }
        except AIUnavailableError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to analyze image with {strategy.get_strategy_name()}: {str(e)}"
            ) from e

    def _to_legacy_vision_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Map canonical image contract to the current parser-compatible payload."""
        foods = []
        for food in payload.get("foods", []):
            macros = food.get("macros", {})
            foods.append(
                {
                    "name": food.get("name"),
                    "quantity": food.get("quantity_g"),
                    "unit": "g",
                    "macros": {
                        "protein": macros.get("protein_g", 0.0),
                        "carbs": macros.get("carbs_g", 0.0),
                        "fat": macros.get("fat_g", 0.0),
                    },
                    "confidence": food.get("confidence", 1.0),
                }
            )

        return {
            "is_food": payload.get("is_food", True),
            "dish_name": payload.get("dish_name"),
            "foods": foods,
            "confidence": payload.get("confidence", 0.5),
            "beverage_metadata": payload.get("beverage_metadata"),
        }

    async def analyze_by_url_with_strategy(
        self, image_url: str, strategy: MealAnalysisStrategy
    ) -> dict[str, Any]:
        """
        Analyze a food image by public URL using the provided analysis strategy.

        Args:
            image_url: Public URL of the image to analyze
            strategy: The analysis strategy to use

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
        """
        image_bytes = await self._fetch_image_url(image_url)
        return await self.analyze_with_strategy(image_bytes, strategy)

    async def _fetch_image_url(self, image_url: str) -> bytes:
        """Fetch bounded image bytes from an HTTP(S) URL."""
        parsed = urlparse(image_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Image URL must be an absolute HTTP(S) URL")

        def _fetch() -> bytes:
            request = Request(image_url, headers={"User-Agent": "MealTrack/1.0"})
            with urlopen(request, timeout=URL_FETCH_TIMEOUT_SECONDS) as response:
                content_type = response.headers.get_content_type()
                if content_type not in ALLOWED_URL_IMAGE_CONTENT_TYPES:
                    raise ValueError(
                        f"Unsupported image URL content type: {content_type}"
                    )
                image_bytes = response.read(MAX_URL_IMAGE_BYTES + 1)
                if len(image_bytes) > MAX_URL_IMAGE_BYTES:
                    raise ValueError("Image URL content too large (max 5MB)")
                return image_bytes

        try:
            return await asyncio.to_thread(_fetch)
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to fetch image URL: {str(e)}") from e

    async def analyze(self, image_bytes: bytes) -> dict[str, Any]:
        """
        Analyze a food image to extract nutritional information.

        Args:
            image_bytes: The raw bytes of the image to analyze

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
        """
        strategy = AnalysisStrategyFactory.create_basic_strategy(
            optimized_prompt_enabled=self._optimized_prompt_enabled
        )
        return await self.analyze_with_strategy(image_bytes, strategy)

    async def analyze_with_portion_context(
        self, image_bytes: bytes, portion_size: float, unit: str
    ) -> dict[str, Any]:
        """
        Analyze a food image with specific portion size context.

        Args:
            image_bytes: The raw bytes of the image to analyze
            portion_size: The target portion size
            unit: The unit of the portion size

        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_portion_strategy(portion_size, unit)
        return await self.analyze_with_strategy(image_bytes, strategy)

    async def analyze_with_ingredients_context(
        self, image_bytes: bytes, ingredients: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyze a food image with known ingredients context.

        Args:
            image_bytes: The raw bytes of the image to analyze
            ingredients: List of ingredient dictionaries with name, quantity, unit

        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_ingredient_strategy(ingredients)
        return await self.analyze_with_strategy(image_bytes, strategy)

    async def analyze_with_weight_context(
        self, image_bytes: bytes, weight_grams: float
    ) -> dict[str, Any]:
        """
        Analyze a food image with specific weight context for accurate nutrition.

        Args:
            image_bytes: The raw bytes of the image to analyze
            weight_grams: The target weight in grams

        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_weight_strategy(weight_grams)
        return await self.analyze_with_strategy(image_bytes, strategy)
