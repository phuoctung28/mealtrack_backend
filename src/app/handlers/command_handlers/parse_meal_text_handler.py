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
from src.infra.adapters.food_data_service import FoodDataService
from src.infra.adapters.fat_secret_service import get_fat_secret_service
from src.domain.services.nutrition_calculation_service import scale_per_100g_nutrition

logger = logging.getLogger(__name__)


@handles(ParseMealTextCommand)
class ParseMealTextHandler(EventHandler[ParseMealTextCommand, ParseMealTextResponse]):
    """Handler for parsing meal text descriptions using Gemini."""

    def __init__(self):
        self._model_manager = GeminiModelManager.get_instance()
        self._food_data_service = FoodDataService()
        self._fat_secret_service = get_fat_secret_service()

    async def handle(self, command: ParseMealTextCommand) -> ParseMealTextResponse:
        # Sanitize user input
        sanitized_text = sanitize_user_description(command.text)

        # Add refinement context if current_items provided
        if command.current_items:
            context = json.dumps(command.current_items, ensure_ascii=False)
            sanitized_text += (
                f"\n\nCurrent meal items:\n{context}\n\n"
                "Update the meal based on my request above. Return the COMPLETE updated list."
            )

        # Get model with JSON response format
        model = self._model_manager.get_model(
            response_mime_type="application/json",
            temperature=0.3,  # Lower temperature for more consistent parsing
        )

        # Build messages with language context
        system_prompt = SystemPrompts.get_meal_text_parsing_prompt(language=command.language)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=sanitized_text),
        ]

        # Call Gemini
        response = await model.ainvoke(messages)
        content = response.content

        # Extract JSON from response
        parsed_items = self._extract_json_from_response(content)

        # Enhance items with USDA/FatSecret cascade lookup
        enhanced_items = []
        for item in parsed_items:
            enhanced = await self._cascade_lookup(item)
            enhanced_items.append(enhanced)

        # Calculate totals
        total_calories = sum(item.get("calories", 0) for item in enhanced_items)
        total_protein = sum(item.get("protein", 0) for item in enhanced_items)
        total_carbs = sum(item.get("carbs", 0) for item in enhanced_items)
        total_fat = sum(item.get("fat", 0) for item in enhanced_items)

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
                data_source=item.get("data_source"),
                fdc_id=item.get("fdc_id"),
            )
            for item in enhanced_items
        ]

        return ParseMealTextResponse(
            items=items,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
        )

    async def _cascade_lookup(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cascade lookup: USDA -> FatSecret -> AI estimate.
        Applies unit-to-grams conversion so nutrition matches what manual-meal stores.
        """
        name = item.get("name", "")
        quantity = item.get("quantity", 1.0)
        unit = item.get("unit", "serving")

        if not name:
            item["data_source"] = "ai_estimate"
            return item

        # AI estimate values (fallback reference)
        ai_calories = item.get("calories", 0)

        # Try USDA first
        try:
            usda_results = await self._food_data_service.search_foods(name, limit=5)
            if usda_results and len(usda_results) > 0:
                usda_food = usda_results[0]
                fdc_id = usda_food.get("fdcId")
                if fdc_id:
                    try:
                        details = await self._food_data_service.get_food_details(fdc_id)
                        nutrients = details.get("foodNutrients", [])
                        per_100g = self._extract_nutrition(nutrients)
                        # Scale per-100g values for the actual quantity+unit
                        scaled = scale_per_100g_nutrition(per_100g, quantity, unit)
                        # Sanity check: reject absurdly low USDA results for non-trivial units
                        non_trivial_units = ("g", "ml", "tsp", "teaspoon")
                        if scaled["calories"] < 5.0 and unit not in non_trivial_units:
                            logger.debug(
                                f"USDA result too low for '{name}' "
                                f"({scaled['calories']} cal/{quantity} {unit}), skipping"
                            )
                            raise ValueError("USDA result unreasonably low")
                        item.update(scaled)
                    except ValueError:
                        raise  # Re-raise sanity check failure to skip USDA
                    except Exception:
                        pass  # Keep AI estimate but use USDA source
                    item["data_source"] = "usda"
                    item["fdc_id"] = fdc_id
                    return item
        except ValueError:
            logger.debug(f"USDA sanity check failed for {name}, trying FatSecret")
        except Exception as e:
            logger.debug(f"USDA lookup failed for {name}: {e}")

        # Try FatSecret
        try:
            fatsecret_results = self._fat_secret_service.search_foods(name, max_results=5)
            if fatsecret_results and len(fatsecret_results) > 0:
                fs_food = fatsecret_results[0]
                per_100g = self._parse_fatsecret_nutrition(fs_food)
                if per_100g:
                    scaled = scale_per_100g_nutrition(per_100g, quantity, unit)
                    item.update(scaled)
                item["data_source"] = "fatsecret"
                return item
        except Exception as e:
            logger.debug(f"FatSecret lookup failed for {name}: {e}")

        # Fallback to AI estimate (values from Gemini prompt, already per-serving)
        item["data_source"] = "ai_estimate"
        return item

    def _parse_fatsecret_nutrition(self, food: Dict[str, Any]) -> Dict[str, float]:
        """Parse per-100g nutrition from FatSecret food_description field.

        FatSecret format: 'Per 100g - Calories: 155kcal | Fat: 11g | Carbs: 1.1g | Protein: 13g'
        """
        desc = food.get("food_description", "")
        if not desc:
            return {}
        result: Dict[str, float] = {}
        try:
            for part in desc.split("|"):
                part = part.strip().lower()
                if "calories" in part or "cal" in part:
                    val = re.search(r'([\d.]+)', part)
                    if val:
                        result["calories"] = float(val.group(1))
                elif "fat" in part:
                    val = re.search(r'([\d.]+)', part)
                    if val:
                        result["fat"] = float(val.group(1))
                elif "carb" in part:
                    val = re.search(r'([\d.]+)', part)
                    if val:
                        result["carbs"] = float(val.group(1))
                elif "protein" in part:
                    val = re.search(r'([\d.]+)', part)
                    if val:
                        result["protein"] = float(val.group(1))
        except Exception as e:
            logger.debug(f"Could not parse FatSecret nutrition: {e}")
            return {}
        return result if result else {}

    def _extract_nutrition(self, nutrients: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract nutrition values from USDA nutrients list."""
        result = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for n in nutrients:
            # USDA format: {"nutrient": {"id": 1008}, "amount": 165.0}
            nutrient_info = n.get("nutrient", {})
            nutrient_id = nutrient_info.get("id")
            value = n.get("amount", 0)
            if nutrient_id in (208, 1008):  # Energy
                result["calories"] = float(value)
            elif nutrient_id in (203, 1003):  # Protein
                result["protein"] = float(value)
            elif nutrient_id in (205, 1005):  # Carbs
                result["carbs"] = float(value)
            elif nutrient_id in (204, 1004):  # Fat
                result["fat"] = float(value)
        return result

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

        # Try to find JSON array (non-greedy to handle multiple bracket groups)
        json_match = re.search(r'\[[\s\S]*?\]', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try stripping leading/trailing non-JSON chars and re-parse
        stripped = content.strip()
        if stripped.startswith('['):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        # Try finding the array after stripping
        match = re.search(r'\[[\s\S]*\]', stripped)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not extract JSON from response: {content[:500]}")
        raise ValueError("Could not parse AI response. Please try again.")
