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
from src.app.services.food_name_localizer import translate_food_texts
from src.domain.exceptions.ai_exceptions import AIOutputValidationError
from src.domain.model.ai.nutrition_contracts import MealTextNutritionResponse
from src.domain.model.nutrition.macros import Macros
from src.domain.model.translation_result import TranslationOutcome
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.ai_output_validation_service import (
    build_validation_retry_prompt,
    validate_ai_output,
)
from src.domain.services.emoji_validator import validate_emoji
from src.domain.services.nutrition_calculation_service import (
    clamp_nutrition_values,
    scale_per_100g_nutrition,
)
from src.domain.services.prompts.input_sanitizer import sanitize_user_description
from src.domain.services.prompts.system_prompts import SystemPrompts

logger = logging.getLogger(__name__)
PARSE_TEXT_VALIDATION_PURPOSE = "parse_text"
MAX_VALIDATION_ATTEMPTS = 2


def _parse_text_fatsecret_timeout_seconds() -> float:
    return float(os.getenv("PARSE_TEXT_FATSECRET_TIMEOUT_SECONDS", "3"))


@handles(ParseMealTextCommand)
class ParseMealTextHandler(
    EventHandler[ParseMealTextCommand, ParseMealTextResponseDto]
):
    """Handler for parsing meal text descriptions using AI."""

    def __init__(
        self,
        meal_generation_service: MealGenerationServicePort,
        fat_secret_service: Any | None = None,
        translation_service: Any | None = None,
    ):
        self._meal_generation_service = meal_generation_service
        self._fat_secret_service = fat_secret_service
        self._translation_service = translation_service

    async def handle(self, command: ParseMealTextCommand) -> ParseMealTextResponseDto:
        # Sanitize user input
        sanitized_text = sanitize_user_description(command.text)
        if not sanitized_text:
            raise ValueError("Invalid or empty meal description.")

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

        validated_payload, raw_payload = await self._generate_parse_text_payload(
            prompt=sanitized_text,
            system_prompt=system_prompt,
        )

        emoji = validate_emoji(validated_payload.get("emoji"))
        parsed_items = self._to_flat_parse_text_items(validated_payload, raw_payload)

        # Enhance items with USDA/fatsecret cascade lookup
        enhanced_items = []
        for item in parsed_items:
            enhanced = await self._cascade_lookup(item, command.language)
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
            for item in enhanced_items:
                item["name"] = self._extract_display_name(
                    item.get("name", "Unknown"), command.language
                )
            await self._translate_structured_english_names(
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
                allowed_units=item.get("allowed_units") or [],
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

    async def _generate_parse_text_payload(
        self, *, prompt: str, system_prompt: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        retry_system_prompt = system_prompt
        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            try:
                raw = await self._meal_generation_service.generate_meal_plan_async(
                    prompt=prompt,
                    system_message=retry_system_prompt,
                    response_type="json",
                    max_tokens=2048,
                    schema=MealTextNutritionResponse,
                    model_purpose="parse_text",
                    thinking_budget=0,
                )
                raw_payload = self._extract_parse_text_payload(raw)
                validated_payload = validate_ai_output(
                    raw_payload,
                    schema=MealTextNutritionResponse,
                    purpose=PARSE_TEXT_VALIDATION_PURPOSE,
                    attempt_count=attempt,
                )
                if attempt > 1:
                    logger.info(
                        "[AI-OUTPUT-VALIDATION-RETRY-SUCCESS] purpose=%s attempt=%s",
                        PARSE_TEXT_VALIDATION_PURPOSE,
                        attempt,
                    )
                return validated_payload, raw_payload
            except AIOutputValidationError as exc:
                logger.warning(
                    "[AI-OUTPUT-VALIDATION-FAILED] purpose=%s attempt=%s detail_count=%s",
                    PARSE_TEXT_VALIDATION_PURPOSE,
                    attempt,
                    len(exc.validation_details),
                )
                if attempt >= MAX_VALIDATION_ATTEMPTS:
                    raise AIOutputValidationError(
                        "Invalid AI output after validation retry",
                        purpose=PARSE_TEXT_VALIDATION_PURPOSE,
                        attempt_count=attempt,
                        validation_details=exc.validation_details,
                    ) from exc
                retry_system_prompt = build_validation_retry_prompt(system_prompt, exc)

        raise RuntimeError("Failed to parse meal text after validation retry")

    def _extract_parse_text_payload(self, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            payload = dict(raw)
        elif isinstance(raw, list):
            payload = {"items": raw}
        else:
            extracted = extract_json_from_response(str(raw))
            payload = {"items": extracted} if isinstance(extracted, list) else extracted

        if not isinstance(payload, dict):
            raise AIOutputValidationError(
                "Invalid AI structured output",
                purpose=PARSE_TEXT_VALIDATION_PURPOSE,
                attempt_count=1,
                validation_details=["response root must be an object or item list"],
            )
        return payload

    def _to_flat_parse_text_items(
        self, validated_payload: dict[str, Any], raw_payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        flat_items = []
        raw_items = raw_payload.get("items", [])
        for index, item in enumerate(validated_payload.get("items", [])):
            macros = item.get("macros", {})
            flat_item = {
                "name": item.get("name"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "english_unit": item.get("english_unit"),
                "protein": macros.get("protein_g", 0.0),
                "carbs": macros.get("carbs_g", 0.0),
                "fat": macros.get("fat_g", 0.0),
                "calories": self._derive_calories_from_macros(macros),
            }
            raw_item = raw_items[index] if index < len(raw_items) else {}
            if isinstance(raw_item, dict):
                english_name = None
                for key in ("english_name", "name_english", "canonical_name"):
                    raw_value = raw_item.get(key)
                    if isinstance(raw_value, str) and raw_value.strip():
                        english_name = raw_value.strip()
                        break
                if english_name:
                    flat_item["english_name"] = english_name
            if item.get("quantity_g") is not None:
                flat_item["quantity_g"] = item["quantity_g"]

            flat_items.append(flat_item)

        return flat_items

    @staticmethod
    def _derive_calories_from_macros(macros: dict[str, Any]) -> float:
        protein = float(macros.get("protein_g", 0.0) or 0.0)
        carbs = float(macros.get("carbs_g", 0.0) or 0.0)
        fiber = float(macros.get("fiber_g", 0.0) or 0.0)
        fat = float(macros.get("fat_g", 0.0) or 0.0)
        return round(Macros.raw_total_calories(protein, carbs, fat, fiber), 2)

    # Max ratio between FatSecret and AI estimate before rejecting FatSecret
    _FATSECRET_DIVERGENCE_THRESHOLD = 3.0

    async def _cascade_lookup(
        self, item: dict[str, Any], language: str = "en"
    ) -> dict[str, Any]:
        """
        Cascade lookup: fatsecret -> AI estimate.
        fatsecret prioritized for precision, but rejected if result diverges
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

        # Try fatsecret — use English name from parentheses for lookup accuracy
        lookup_name = item.get("english_name") or (
            self._extract_english_name(name) if language != "en" else name
        )
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

                    # Reject fatsecret if it diverges >3x from AI estimate
                    # (indicates wrong product match, e.g. concentrate vs liquid)
                    if ai_calories > 0 and fs_calories > 0:
                        ratio = fs_calories / ai_calories
                        if ratio > self._FATSECRET_DIVERGENCE_THRESHOLD:
                            logger.warning(
                                "fatsecret result rejected: calorie divergence exceeded threshold"
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
            logger.debug("fatsecret lookup failed error_type=%s", type(e).__name__)

        # Fallback to AI estimate (values from prompt, already per-serving)
        item["data_source"] = "ai_estimate"
        return item

    async def _translate_structured_english_names(
        self, items: list[dict[str, Any]], language: str
    ) -> None:
        """Translate only names explicitly identified as English by the payload."""
        if self._translation_service is None:
            return
        candidates = [
            str(item["english_name"])
            for item in items
            if isinstance(item.get("english_name"), str)
            and item["english_name"].strip()
            and item.get("name") == item.get("english_name")
        ]
        if not candidates:
            return
        result = await translate_food_texts(
            candidates,
            target_language=language,
            translation_service=self._translation_service,
        )
        if result.outcome not in {
            TranslationOutcome.TRANSLATED,
            TranslationOutcome.PARTIAL,
        }:
            return
        translated_by_source = dict(zip(candidates, result.texts, strict=False))
        for item in items:
            english_name = item.get("english_name")
            if english_name and item.get("name") == english_name:
                item["name"] = translated_by_source.get(english_name, english_name)

    @staticmethod
    def _extract_english_name(name: str) -> str:
        """Extract the structurally required English suffix from parse output."""
        match = re.search(r"^(.+?)\s*\(([^)]+)\)$", name.strip())
        if not match:
            return name
        return match.group(2).strip()

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
        before = match.group(1)
        # The non-English prompt structurally defines local text first and
        # English canonical text in the parenthesized suffix.
        return before.strip()
