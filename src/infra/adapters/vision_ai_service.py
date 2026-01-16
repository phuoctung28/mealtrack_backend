import base64
import json
import logging
import re
from typing import Dict, Any, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.strategies.meal_analysis_strategy import (
    MealAnalysisStrategy,
    AnalysisStrategyFactory
)
from src.infra.services.ai.gemini_model_manager import GeminiModelManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class VisionAIService(VisionAIServicePort):
    """
    Implementation of VisionAIServicePort using Google Gemini API.
    
    This class implements US-2.1 - Call Vision AI to get nutrition estimate.
    """
    
    def __init__(self):
        """Initialize the Gemini client using singleton manager."""
        self._model_manager = GeminiModelManager.get_instance()
        # Use standard temperature=0.7 to share model instance across all services
        self.model = self._model_manager.get_model()
        
    def analyze_with_strategy(self, image_bytes: bytes, strategy: MealAnalysisStrategy) -> Dict[str, Any]:
        """
        Analyze a food image using the provided analysis strategy.

        Args:
            image_bytes: The raw bytes of the image to analyze
            strategy: The analysis strategy to use

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
        """
        try:
            # Encode image for the API
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Create message with the image using strategy
            messages = [
                SystemMessage(content=strategy.get_analysis_prompt()),
                HumanMessage(
                    content=[
                        {"type": "text", "text": strategy.get_user_message()},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                )
            ]

            # Call the API
            response = self.model.invoke(messages)

            # Parse the response to extract the JSON
            content = response.content

            # Validate response content is not empty
            if not content or (isinstance(content, str) and not content.strip()):
                # Check for safety blocking or other issues
                response_metadata = getattr(response, 'response_metadata', {})
                finish_reason = response_metadata.get('finish_reason', 'unknown')
                safety_ratings = response_metadata.get('safety_ratings', [])

                logger.warning(
                    f"Empty response from Gemini API. finish_reason={finish_reason}, "
                    f"safety_ratings={safety_ratings}"
                )

                if finish_reason == 'SAFETY':
                    raise ValueError(
                        "Image was blocked by AI safety filters. "
                        "Please try a different image of food."
                    )
                raise ValueError(
                    f"AI returned empty response (finish_reason: {finish_reason}). "
                    "The image may not be clear or recognizable as food."
                )

            # Extract JSON from the response
            result = self._extract_json_from_response(content)

            return {
                "raw_response": content,
                "structured_data": result,
                "strategy_used": strategy.get_strategy_name()
            }

        except Exception as e:
            raise RuntimeError(f"Failed to analyze image with {strategy.get_strategy_name()}: {str(e)}")

    def _extract_json_from_response(self, content: str) -> Dict[str, Any]:
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
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find any complete JSON object
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Detect truncated response (has opening { but no closing })
        if '{' in content and '}' not in content:
            logger.error(f"Truncated JSON response detected: {content[:500]}")
            raise ValueError(
                "AI response was truncated. Please try again with a simpler image."
            )

        logger.error(f"Could not extract JSON from response: {content[:500]}")
        raise ValueError(
            "Could not extract JSON from AI response. "
            "Please try again or use a clearer image."
        )
        
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze a food image to extract nutritional information.

        Args:
            image_bytes: The raw bytes of the image to analyze

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
        """
        strategy = AnalysisStrategyFactory.create_basic_strategy()
        return self.analyze_with_strategy(image_bytes, strategy)

    def analyze_with_portion_context(
        self, image_bytes: bytes, portion_size: float, unit: str
    ) -> Dict[str, Any]:
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
        return self.analyze_with_strategy(image_bytes, strategy)

    def analyze_with_ingredients_context(
        self, image_bytes: bytes, ingredients: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a food image with known ingredients context.

        Args:
            image_bytes: The raw bytes of the image to analyze
            ingredients: List of ingredient dictionaries with name, quantity, unit

        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_ingredient_strategy(ingredients)
        return self.analyze_with_strategy(image_bytes, strategy)

    def analyze_with_weight_context(
        self, image_bytes: bytes, weight_grams: float
    ) -> Dict[str, Any]:
        """
        Analyze a food image with specific weight context for accurate nutrition.

        Args:
            image_bytes: The raw bytes of the image to analyze
            weight_grams: The target weight in grams

        Returns:
            JSON-compatible dictionary with the raw AI response
        """
        strategy = AnalysisStrategyFactory.create_weight_strategy(weight_grams)
        return self.analyze_with_strategy(image_bytes, strategy) 