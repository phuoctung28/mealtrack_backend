"""
Handler for parsing natural language meal text into structured food items.
"""
import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.events.base import EventHandler, handles
from src.app.schemas.meal_schemas import ParseMealTextResponseDto, ParsedFoodItemDto
from src.domain.services.prompts.input_sanitizer import sanitize_user_description
from src.infra.services.ai.gemini_model_manager import GeminiModelManager
from src.infra.services.ai.prompts.system_prompts import SystemPrompts
from src.infra.adapters.fat_secret_service import get_fat_secret_service
from src.domain.services.nutrition_calculation_service import (
    scale_per_100g_nutrition,
    clamp_nutrition_values,
)
from src.app.handlers.command_handlers.meal_text_parsing_utils import (
    extract_json_from_response,
    extract_usda_nutrition,
    parse_fatsecret_nutrition,
)
from src.domain.services.meal_suggestion.translation_service import TranslationService
from src.infra.adapters.meal_generation_service import MealGenerationService

logger = logging.getLogger(__name__)


@handles(ParseMealTextCommand)
class ParseMealTextHandler(EventHandler[ParseMealTextCommand, ParseMealTextResponseDto]):
    """Handler for parsing meal text descriptions using Gemini."""

    def __init__(self):
        self._model_manager = GeminiModelManager.get_instance()
        self._fat_secret_service = get_fat_secret_service()
        self._translation_service = TranslationService(MealGenerationService())

    async def handle(self, command: ParseMealTextCommand) -> ParseMealTextResponseDto:
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

        # Build messages — always English for better AI accuracy
        system_prompt = SystemPrompts.get_meal_text_parsing_prompt()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=sanitized_text),
        ]

        # Call Gemini
        response = await model.ainvoke(messages)
        content = response.content

        # Extract JSON from response
        parsed_items = extract_json_from_response(content)

        # Enhance items with USDA/FatSecret cascade lookup
        enhanced_items = []
        for item in parsed_items:
            enhanced = await self._cascade_lookup(item)
            enhanced_items.append(enhanced)

        # Clamp nutrition to physically plausible ranges
        for item in enhanced_items:
            clamped = clamp_nutrition_values(item)
            item.update(clamped)

        # Calculate totals
        total_protein = sum(item.get("protein", 0) for item in enhanced_items)
        total_carbs = sum(item.get("carbs", 0) for item in enhanced_items)
        total_fat = sum(item.get("fat", 0) for item in enhanced_items)

        # Translate food names if non-English
        if command.language and command.language != "en":
            names = [item.get("name", "Unknown") for item in enhanced_items]
            try:
                translated = await self._translation_service._batch_translate(
                    names, command.language
                )
                for item, name in zip(enhanced_items, translated):
                    item["name"] = name
            except Exception as e:
                logger.warning(f"Name translation failed, using English: {e}")

        # Build response items
        items = [
            ParsedFoodItemDto(
                name=item.get("name", "Unknown"),
                quantity=item.get("quantity", 1),
                unit=item.get("unit", "serving"),
                protein=item.get("protein", 0),
                carbs=item.get("carbs", 0),
                fat=item.get("fat", 0),
                data_source=item.get("data_source"),
                fdc_id=item.get("fdc_id"),
            )
            for item in enhanced_items
        ]

        return ParseMealTextResponseDto(
            items=items,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
        )

    # Max ratio between FatSecret and AI estimate before rejecting FatSecret
    _FATSECRET_DIVERGENCE_THRESHOLD = 3.0

    async def _cascade_lookup(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cascade lookup: FatSecret -> AI estimate.
        FatSecret prioritized for precision, but rejected if result diverges
        >3x from AI estimate (indicates wrong product match).
        """
        name = item.get("name", "")
        quantity = item.get("quantity", 1.0)
        unit = item.get("unit", "serving")

        if not name:
            item["data_source"] = "ai_estimate"
            return item

        # Save AI's original calorie estimate for sanity check
        ai_calories = item.get("calories", 0)

        # Try FatSecret (more precise for common foods)
        try:
            fatsecret_results = await self._fat_secret_service.search_foods(name, max_results=5)
            if fatsecret_results and len(fatsecret_results) > 0:
                fs_food = fatsecret_results[0]
                per_100g = parse_fatsecret_nutrition(fs_food)
                allowed_units = fs_food.get("allowed_units")
                if per_100g:
                    scaled = scale_per_100g_nutrition(per_100g, quantity, unit, allowed_units=allowed_units, food_name=name)
                    fs_calories = scaled.get("calories", 0)

                    # Reject FatSecret if it diverges >3x from AI estimate
                    # (indicates wrong product match, e.g. concentrate vs liquid)
                    if ai_calories > 0 and fs_calories > 0:
                        ratio = fs_calories / ai_calories
                        if ratio > self._FATSECRET_DIVERGENCE_THRESHOLD:
                            logger.warning(
                                f"FatSecret rejected for '{name}': "
                                f"{fs_calories:.0f} kcal vs AI {ai_calories:.0f} kcal "
                                f"(ratio {ratio:.1f}x > {self._FATSECRET_DIVERGENCE_THRESHOLD}x)"
                            )
                            item["data_source"] = "ai_estimate"
                            return item

                    item.update(scaled)
                # Pass allowed_units for frontend display
                if allowed_units:
                    item["allowed_units"] = allowed_units
                item["data_source"] = "fatsecret"
                return item
        except Exception as e:
            logger.debug(f"FatSecret lookup failed for {name}: {e}")

        # Fallback to AI estimate (values from Gemini prompt, already per-serving)
        item["data_source"] = "ai_estimate"
        return item
