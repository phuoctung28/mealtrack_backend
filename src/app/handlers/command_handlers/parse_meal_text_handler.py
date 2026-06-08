"""
Handler for parsing natural language meal text into structured food items.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any

from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.meal_text_parsing_utils import (
    extract_json_from_response,
    parse_fatsecret_nutrition,
)
from src.app.schemas.meal_schemas import ParsedFoodItemDto, ParseMealTextResponseDto
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.emoji_validator import validate_emoji
from src.domain.services.nutrition_calculation_service import (
    clamp_nutrition_values,
    scale_per_100g_nutrition,
)
from src.domain.services.prompts.input_sanitizer import sanitize_user_description
from src.domain.services.prompts.system_prompts import SystemPrompts
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)

logger = logging.getLogger(__name__)


def _parse_text_fatsecret_timeout_seconds() -> float:
    return float(os.getenv("PARSE_TEXT_FATSECRET_TIMEOUT_SECONDS", "3"))


@handles(ParseMealTextCommand)
class ParseMealTextHandler(
    EventHandler[ParseMealTextCommand, ParseMealTextResponseDto]
):
    """Handler for parsing meal text descriptions using Gemini."""

    def __init__(
        self,
        meal_generation_service: MealGenerationServicePort,
        fat_secret_service: Any | None = None,
        translation_service: DeepLTextTranslationService | None = None,
    ):
        self._meal_generation_service = meal_generation_service
        self._fat_secret_service = fat_secret_service
        self._translation_service = translation_service

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

        # Build messages with locale-aware food names
        system_prompt = SystemPrompts.get_meal_text_parsing_prompt(
            language=command.language
        )

        raw = await asyncio.to_thread(
            self._meal_generation_service.generate_meal_plan,
            prompt=sanitized_text,
            system_message=system_prompt,
            response_type="json",
            max_tokens=2048,
            model_purpose="parse_text",
            thinking_budget=0,
        )

        # Extract JSON from response — may be {emoji, items: [...]} or plain [...]
        emoji = None
        if isinstance(raw, dict):
            emoji = validate_emoji(raw.get("emoji"))
            parsed_items = raw.get("items", [])
            if not isinstance(parsed_items, list):
                parsed_items = [parsed_items]
        elif isinstance(raw, list):
            parsed_items = raw
        else:
            parsed_items = extract_json_from_response(str(raw))

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

        # Localize names for non-English users
        if command.language and command.language != "en":
            # Step 1: Strip bilingual parentheses
            for item in enhanced_items:
                item["name"] = self._extract_display_name(
                    item.get("name", "Unknown"), command.language
                )
            # Step 2: Translate any remaining English names using DeepL
            if self._translation_service:
                await self._translate_english_names_deepl(
                    enhanced_items, command.language
                )

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
            emoji=emoji,
        )

    # Max ratio between FatSecret and AI estimate before rejecting FatSecret
    _FATSECRET_DIVERGENCE_THRESHOLD = 3.0

    async def _cascade_lookup(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Cascade lookup: FatSecret -> AI estimate.
        FatSecret prioritized for precision, but rejected if result diverges
        >3x from AI estimate (indicates wrong product match).
        Uses english_unit (from AI) for calculation; unit stays localized for display.
        """
        name = item.get("name", "")
        quantity = item.get("quantity", 1.0)
        # Prefer english_unit for calculation, fall back to unit
        unit = item.get("english_unit") or item.get("unit", "serving")

        if not name:
            item["data_source"] = "ai_estimate"
            return item

        # Save AI's original calorie estimate for sanity check
        ai_calories = item.get("calories", 0)

        # Try FatSecret — use English name from parentheses for lookup accuracy
        lookup_name = self._extract_english_name(name)
        try:
            if not self._fat_secret_service:
                item["data_source"] = "ai_estimate"
                return item

            fatsecret_results = await asyncio.wait_for(
                self._fat_secret_service.search_foods(lookup_name, max_results=5),
                timeout=_parse_text_fatsecret_timeout_seconds(),
            )
            if fatsecret_results and len(fatsecret_results) > 0:
                fs_food = fatsecret_results[0]
                per_100g = parse_fatsecret_nutrition(fs_food)
                allowed_units = fs_food.get("allowed_units")
                if per_100g:
                    scaled = scale_per_100g_nutrition(
                        per_100g,
                        quantity,
                        unit,
                        allowed_units=allowed_units,
                        food_name=lookup_name,
                    )
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

    @staticmethod
    def _is_english(name: str) -> bool:
        """Check if name is likely English (ASCII-only, ignoring digits/punct)."""
        letters = [c for c in name if c.isalpha()]
        return bool(letters) and all(ord(c) < 128 for c in letters)

    async def _translate_english_names_deepl(
        self, items: list[dict[str, Any]], language: str
    ) -> None:
        """Detect and batch-translate any remaining English food names using DeepL."""
        english_indices = [
            i for i, item in enumerate(items) if self._is_english(item.get("name", ""))
        ]
        if not english_indices:
            return

        names_to_translate = [items[i]["name"] for i in english_indices]
        logger.info(
            f"Translating {len(names_to_translate)} English names to {language} via DeepL"
        )

        try:
            translated = await self._translation_service.translate_texts(
                names_to_translate, language
            )

            if len(translated) == len(english_indices):
                for idx, name in zip(english_indices, translated, strict=False):
                    if isinstance(name, str) and name.strip():
                        items[idx]["name"] = name.strip()
            else:
                logger.warning("DeepL translation response length mismatch, skipping")
        except Exception as e:
            logger.warning(f"DeepL name translation failed, keeping English: {e}")

    @staticmethod
    def _extract_english_name(name: str) -> str:
        """Extract English name for FatSecret lookup.

        AI may return either format:
        - 'English Name (Local Name)' → extract before parens
        - 'Local Name (English Name)' → extract inside parens
        Heuristic: if text inside parens is ASCII, it's English; otherwise
        the text before parens is English.
        """
        match = re.search(r"^(.+?)\s*\(([^)]+)\)$", name.strip())
        if not match:
            return name
        before, inside = match.group(1), match.group(2)
        # If inside parens is mostly ASCII → it's the English name
        if all(ord(c) < 256 for c in inside.replace(" ", "")):
            return inside
        return before

    @staticmethod
    def _extract_display_name(name: str, language: str) -> str:
        """Strip parenthesized portion, keep only the user's language.

        'Sliced Beef (Thịt bò)' + vi → 'Thịt bò'
        'Thịt bò (Sliced Beef)' + vi → 'Thịt bò'
        'Eggs' (no parens) → 'Eggs'
        """
        match = re.search(r"^(.+?)\s*\(([^)]+)\)$", name.strip())
        if not match:
            return name
        before, inside = match.group(1), match.group(2)
        # Non-ASCII part is the local language name
        before_ascii = all(ord(c) < 256 for c in before.replace(" ", ""))
        if before_ascii:
            return inside  # Local name is inside parens
        return before  # Local name is before parens
