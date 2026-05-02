"""JSON extraction utilities for meal suggestion responses."""

import json
import re


class JsonExtractor:
    """Extracts JSON from AI responses."""

    @staticmethod
    def extract_json(content: str) -> dict:
        """Extract JSON from AI response."""
        try:
            # Try direct parsing
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Try to find JSON in markdown code block
            json_match = re.search(r"```json(.*?)```", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1).strip())

            # Try to find any JSON-like structure
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

            raise ValueError("Could not extract JSON from response") from e

    @staticmethod
    def extract_unified_meals_json(content: str) -> dict:
        """Extract JSON from unified meal response."""
        try:
            # Try direct parsing
            data = json.loads(content)

            # Validate structure
            if "meals" not in data or not isinstance(data["meals"], list):
                raise ValueError("Response missing 'meals' array")

            return data

        except json.JSONDecodeError as e:
            # Try to find JSON in markdown code block
            json_match = re.search(r"```json(.*?)```", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1).strip())
                if "meals" not in data or not isinstance(data["meals"], list):
                    raise ValueError("Response missing 'meals' array") from e
                return data

            # Try to find any JSON-like structure
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if "meals" not in data or not isinstance(data["meals"], list):
                    raise ValueError("Response missing 'meals' array") from e
                return data

            raise ValueError(
                "Could not extract unified meals JSON from response"
            ) from e
