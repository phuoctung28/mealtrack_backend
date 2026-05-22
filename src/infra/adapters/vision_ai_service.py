import json
import logging
import re
from io import BytesIO
from typing import Any

from PIL import Image

from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.strategies.meal_analysis_strategy import (
    AnalysisStrategyFactory,
    MealAnalysisStrategy,
)
from src.infra.services.ai.ai_model_manager import AIModelManager, ModelPurpose

logger = logging.getLogger(__name__)


class VisionAIService(VisionAIServicePort):
    """Vision AI service with automatic fallback on failures."""

    def __init__(self):
        """Initialize with AI model manager."""
        self._ai_manager = AIModelManager.get_instance()
        self._optimized_prompt_enabled = True

    def _compress_image(self, image_bytes: bytes) -> bytes:
        """Compress image for faster upload."""
        try:
            img = Image.open(BytesIO(image_bytes))
            w, h = img.size

            if (
                img.format == "JPEG"
                and max(w, h) <= 768
                and len(image_bytes) < 200 * 1024
            ):  # already small JPEG
                return image_bytes

            if max(w, h) > 768:
                ratio = 768 / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

            if img.mode != "RGB":
                img = img.convert("RGB")

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except Exception as exc:
            logger.warning("Image compression failed, using original: %s", exc)
            return image_bytes

    def _extract_json_from_response(self, content: str) -> dict[str, Any]:
        """
        Extract JSON from AI response, handling various formats.

        Args:
            content: The raw response string from the AI

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If JSON cannot be extracted
        """
        # Try to parse the entire response as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code block (with closing ```)
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find any complete JSON object
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Detect truncated response:
        # 1. Has opening { but no closing }
        # 2. Unbalanced braces (more { than })
        # 3. Ends mid-string (common truncation pattern)
        open_braces = content.count("{")
        close_braces = content.count("}")
        is_truncated = (
            (open_braces > 0 and close_braces == 0)
            or (open_braces > close_braces)
            or content.rstrip().endswith(('":', '": "', '"name": "', '",'))
        )

        if is_truncated:
            logger.error(f"Truncated JSON response detected: {content[:500]}")
            raise ValueError(
                "AI response was truncated. Please try again with a simpler image."
            )

        logger.error(f"Could not extract JSON from response: {content[:500]}")
        raise ValueError(
            "Could not extract JSON from AI response. "
            "Please try again or use a clearer image."
        )

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

        try:
            result = await self._ai_manager.generate_with_vision(
                purpose=ModelPurpose.MEAL_SCAN,
                prompt=strategy.get_user_message(),
                image_data=image_bytes,
                system_message=strategy.get_analysis_prompt(),
                max_tokens=1024,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to analyze image with {strategy.get_strategy_name()}: {str(e)}"
            ) from e

        return {
            "raw_response": json.dumps(result),
            "structured_data": result,
            "strategy_used": strategy.get_strategy_name(),
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
        try:
            result = await self._ai_manager.generate_with_vision(
                purpose=ModelPurpose.MEAL_SCAN,
                prompt=strategy.get_user_message(),
                image_data=image_url.encode("utf-8"),
                system_message=strategy.get_analysis_prompt(),
                max_tokens=1024,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to analyze image URL with {strategy.get_strategy_name()}: {str(e)}"
            ) from e

        return {
            "raw_response": json.dumps(result),
            "structured_data": result,
            "strategy_used": strategy.get_strategy_name(),
        }

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

    async def analyze_by_url(self, image_url: str) -> dict[str, Any]:
        """
        Analyze a food image from a public URL.
        """
        strategy = AnalysisStrategyFactory.create_basic_strategy(
            optimized_prompt_enabled=self._optimized_prompt_enabled
        )
        return await self.analyze_by_url_with_strategy(image_url, strategy)

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
