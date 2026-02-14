"""
Handler for parsing natural language meal text into structured food items.
"""
import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.events.base import EventHandler, handles
from src.api.schemas.response.meal_responses import ParseMealTextResponse, ParsedFoodItem
from src.domain.services.prompts.input_sanitizer import sanitize_user_description
from src.infra.services.ai.gemini_model_manager import GeminiModelManager
from src.infra.services.ai.prompts.system_prompts import SystemPrompts

logger = logging.getLogger(__name__)


@handles(ParseMealTextCommand)
class ParseMealTextHandler(EventHandler[ParseMealTextCommand, ParseMealTextResponse]):
    """Handler for parsing meal text descriptions using Gemini."""

    def __init__(self):
        self._model_manager = GeminiModelManager.get_instance()

    async def handle(self, command: ParseMealTextCommand) -> ParseMealTextResponse:
        # Sanitize user input
        sanitized_text = sanitize_user_description(command.text)

        # Get model with JSON response format
        model = self._model_manager.get_model(
            response_mime_type="application/json",
            temperature=0.3,  # Lower temperature for more consistent parsing
        )

        # Build messages
        system_prompt = SystemPrompts.get_meal_text_parsing_prompt()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=sanitized_text),
        ]

        # Call Gemini
        response = await model.ainvoke(messages)
        content = response.content

        # Extract JSON from response
        parsed_items = self._extract_json_from_response(content)

        # Calculate totals
        total_calories = sum(item.get("calories", 0) for item in parsed_items)
        total_protein = sum(item.get("protein", 0) for item in parsed_items)
        total_carbs = sum(item.get("carbs", 0) for item in parsed_items)
        total_fat = sum(item.get("fat", 0) for item in parsed_items)

        # Build response items
        items = [
            ParsedFoodItem(
                name=item.get("name", "Unknown"),
                quantity=item.get("quantity", 1),
                unit=item.get("unit", "serving"),
                calories=item.get("calories", 0),
                protein=item.get("protein", 0),
                carbs=item.get("carbs", 0),
                fat=item.get("fat", 0),
            )
            for item in parsed_items
        ]

        return ParseMealTextResponse(
            items=items,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
        )

    def _extract_json_from_response(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract JSON array from AI response.

        Args:
            content: The raw response string from the AI

        Returns:
            List of parsed food items

        Raises:
            ValueError: If JSON cannot be extracted
        """
        # Try to parse the entire response as JSON
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
            return [result]
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if json_match:
            try:
                result = json.loads(json_match.group(1).strip())
                if isinstance(result, list):
                    return result
                return [result]
            except json.JSONDecodeError:
                pass

        # Try to find JSON array
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not extract JSON from response: {content[:500]}")
        raise ValueError("Could not parse AI response. Please try again.")
