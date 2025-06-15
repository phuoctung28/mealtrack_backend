"""
Ingredient Extraction Service

Application layer service for extracting ingredient breakdown from AI responses.
This service handles the business logic of parsing raw AI responses and converting
them to structured ingredient data.

Following Clean Architecture:
- This belongs in the Application layer (app/) as it contains business logic
- API layer mappers should only handle DTO conversions, not business logic
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from domain.model.macros import Macros
from domain.model.meal import Meal

logger = logging.getLogger(__name__)


@dataclass
class IngredientData:
    """Application layer ingredient data model."""
    name: str
    quantity: float
    unit: str
    calories: float
    macros: Macros


@dataclass
class MealAnalysisData:
    """Application layer meal analysis data model."""
    meal_name: Optional[str]
    ingredients: List[IngredientData]


class IngredientExtractionService:
    """
    Service for extracting ingredient breakdown from AI responses.
    
    This service encapsulates the business logic for:
    - Parsing raw AI responses
    - Extracting ingredient data
    - Converting to structured format
    - Error handling and validation
    """
    
    def extract_meal_analysis_from_meal(self, meal: Meal) -> Optional[MealAnalysisData]:
        """
        Extract both meal name and ingredient breakdown from a meal's raw AI response.
        
        Args:
            meal: Domain meal model
            
        Returns:
            MealAnalysisData with meal name and ingredients, or None if no data available
        """
        # Check if we have raw AI response
        if not hasattr(meal, 'raw_gpt_json') or not meal.raw_gpt_json:
            logger.debug(f"No raw AI response available for meal {meal.meal_id}")
            return None
        
        # Check if raw_gpt_json is empty string
        if not meal.raw_gpt_json.strip():
            logger.debug(f"Empty raw AI response for meal {meal.meal_id}")
            return None
        
        try:
            # Parse the raw GPT JSON response
            raw_response = self._parse_raw_response(meal.raw_gpt_json)
            if not raw_response:
                logger.debug(f"Failed to parse raw response for meal {meal.meal_id}")
                return None
            
            # Extract structured data
            structured_data = self._extract_structured_data(raw_response)
            if not structured_data:
                logger.debug(f"No structured data found for meal {meal.meal_id}")
                return None
            
            # Extract meal name
            meal_name = structured_data.get('meal_name')
            
            # Extract foods array
            foods = self._extract_foods_array(structured_data)
            if not foods:
                logger.debug(f"No foods array found for meal {meal.meal_id}")
                # Return with meal name even if no ingredients
                return MealAnalysisData(meal_name=meal_name, ingredients=[])
            
            # Convert to ingredient data objects
            ingredients = self._convert_to_ingredient_data(foods)
            
            logger.info(f"Extracted meal analysis from meal {meal.meal_id}: '{meal_name}' with {len(ingredients)} ingredients")
            return MealAnalysisData(meal_name=meal_name, ingredients=ingredients)
            
        except Exception as e:
            logger.warning(f"Error extracting meal analysis from meal {meal.meal_id}: {e}")
            return None

    def extract_ingredients_from_meal(self, meal: Meal) -> Optional[List[IngredientData]]:
        """
        Extract ingredient breakdown from a meal's raw AI response.
        
        Args:
            meal: Domain meal model
            
        Returns:
            List of IngredientData objects, or None if no data available
        """
        analysis = self.extract_meal_analysis_from_meal(meal)
        return analysis.ingredients if analysis else None
    
    def _parse_raw_response(self, raw_gpt_json: str) -> Optional[Dict[str, Any]]:
        """Parse the raw GPT JSON response."""
        try:
            # Check if the string is empty or just whitespace
            if not raw_gpt_json.strip():
                logger.debug("Raw GPT JSON is empty")
                return None
            
            # Handle markdown code block formatting
            cleaned_json = self._clean_markdown_json(raw_gpt_json)
            
            return json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse raw GPT JSON: {e}")
            logger.debug(f"Raw JSON content (first 200 chars): {raw_gpt_json[:200]}")
            return None
    
    def _clean_markdown_json(self, raw_json: str) -> str:
        """
        Clean markdown code block formatting from JSON string.
        
        Handles cases where the JSON is wrapped in markdown code blocks like:
        ```json
        { ... }
        ```
        """
        # Strip whitespace
        cleaned = raw_json.strip()
        
        # Remove markdown code block start (```json or ```)
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]  # Remove ```json
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]   # Remove ```
        
        # Remove markdown code block end (```)
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]  # Remove trailing ```
        
        # Strip any remaining whitespace
        return cleaned.strip()
    
    def _extract_structured_data(self, raw_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract structured data from the raw response."""
        # First try to find structured_data wrapper
        if "structured_data" in raw_response:
            return raw_response["structured_data"]
        
        # If no structured_data wrapper, the response might be the structured data itself
        # Check if it has the expected structure (foods array)
        if "foods" in raw_response:
            logger.debug("Using raw response as structured data (no wrapper found)")
            return raw_response
        
        logger.debug("No structured_data or foods found in raw response")
        return None
    
    def _extract_foods_array(self, structured_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Extract foods array from structured data."""
        if "foods" not in structured_data:
            logger.debug("No foods array found in structured data")
            return None
        
        foods = structured_data["foods"]
        if not isinstance(foods, list) or len(foods) == 0:
            logger.debug("Foods array is empty or invalid")
            return None
        
        return foods
    
    def _convert_to_ingredient_data(self, foods: List[Dict[str, Any]]) -> List[IngredientData]:
        """Convert food items to IngredientData objects."""
        ingredients = []
        
        for food_item in foods:
            try:
                ingredient = self._parse_food_item(food_item)
                if ingredient:
                    ingredients.append(ingredient)
            except Exception as e:
                logger.warning(f"Failed to parse food item: {e}")
                continue
        
        return ingredients
    
    def _parse_food_item(self, food_item: Dict[str, Any]) -> Optional[IngredientData]:
        """Parse a single food item into IngredientData."""
        try:
            # Validate required fields
            required_fields = ["name", "quantity", "unit", "calories", "macros"]
            for field in required_fields:
                if field not in food_item:
                    logger.warning(f"Missing required field '{field}' in food item")
                    return None
            
            # Extract macros
            macros_data = food_item["macros"]
            macros = Macros(
                protein=float(macros_data.get("protein", 0)),
                carbs=float(macros_data.get("carbs", 0)),
                fat=float(macros_data.get("fat", 0)),
                fiber=float(macros_data.get("fiber", 0)) if macros_data.get("fiber") is not None else None
            )
            
            # Create ingredient data
            ingredient = IngredientData(
                name=str(food_item["name"]),
                quantity=float(food_item["quantity"]),
                unit=str(food_item["unit"]),
                calories=float(food_item["calories"]),
                macros=macros
            )
            
            # Basic validation
            if ingredient.quantity <= 0:
                logger.warning(f"Invalid quantity for ingredient {ingredient.name}: {ingredient.quantity}")
                return None
            
            if ingredient.calories < 0:
                logger.warning(f"Invalid calories for ingredient {ingredient.name}: {ingredient.calories}")
                return None
            
            return ingredient
            
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Error parsing food item: {e}")
            return None 