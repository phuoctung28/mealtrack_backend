"""
AI response parser for handling structured responses from AI services.
Extracts parsing logic to make it reusable and testable.
"""
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class AIResponseParser:
    """
    Parser for AI chat responses.

    Handles JSON-formatted responses with structured data like
    meal suggestions, follow-up questions, etc.
    """

    @staticmethod
    def parse_response(content: str) -> Dict[str, Any]:
        """
        Parse AI response and extract structured data.

        Args:
            content: Raw AI response content (potentially JSON)

        Returns:
            Dictionary with:
            - message: The display message (str)
            - follow_ups: List of follow-up questions (list)
            - structured_data: Meal suggestions and other data (dict or None)
        """
        try:
            # Try to parse as JSON
            # Handle potential markdown code blocks
            clean_content = content.strip()

            # Remove markdown code block delimiters
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]

            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]

            clean_content = clean_content.strip()

            # Parse JSON
            parsed = json.loads(clean_content)

            return {
                "message": parsed.get("message", content),
                "follow_ups": AIResponseParser._parse_follow_ups(
                    parsed.get("follow_ups", [])
                ),
                "structured_data": AIResponseParser._parse_structured_data(parsed)
            }

        except json.JSONDecodeError as e:
            logger.warning(f"AI response not in JSON format: {e}")
            # Fallback: return raw content with no structured data
            return {
                "message": content,
                "follow_ups": [],
                "structured_data": None
            }

    @staticmethod
    def _parse_follow_ups(follow_ups_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse and validate follow-up questions.

        Args:
            follow_ups_raw: Raw follow-up data from AI

        Returns:
            List of validated follow-up dictionaries
        """
        validated_follow_ups = []

        for i, follow_up in enumerate(follow_ups_raw):
            if not isinstance(follow_up, dict):
                continue

            validated_follow_ups.append({
                "id": follow_up.get("id", f"followup_{i}"),
                "text": follow_up.get("text", ""),
                "type": follow_up.get("type", "question"),
                "metadata": follow_up.get("metadata")
            })

        return validated_follow_ups

    @staticmethod
    def _parse_structured_data(parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse structured data like meals and recipes.

        Args:
            parsed: Parsed JSON response

        Returns:
            Structured data dictionary or None if no data present
        """
        meals = parsed.get("meals", [])
        recipes = parsed.get("recipes", [])

        # Only return structured data if we have content
        if meals or recipes:
            return {
                "meals": AIResponseParser._validate_meals(meals),
                "recipes": recipes  # Could add validation here too
            }

        return None

    @staticmethod
    def _validate_meals(meals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate meal data structure.

        Args:
            meals: List of meal dictionaries

        Returns:
            List of validated meal dictionaries
        """
        validated_meals = []

        for meal in meals:
            if not isinstance(meal, dict):
                continue

            # Ensure required fields exist
            validated_meal = {
                "name": meal.get("name", "Unknown Meal"),
                "ingredients": meal.get("ingredients", []),
                "difficulty": meal.get("difficulty", "medium"),
                "cook_time": meal.get("cook_time", "Unknown"),
                "description": meal.get("description", "")
            }

            validated_meals.append(validated_meal)

        return validated_meals

    @staticmethod
    def is_json_response(content: str) -> bool:
        """
        Check if content appears to be JSON formatted.

        Args:
            content: Content to check

        Returns:
            True if content appears to be JSON
        """
        clean_content = content.strip()

        # Check for markdown code blocks
        if clean_content.startswith("```"):
            return True

        # Check for JSON object start
        if clean_content.startswith("{") and clean_content.endswith("}"):
            try:
                json.loads(clean_content)
                return True
            except json.JSONDecodeError:
                return False

        return False
