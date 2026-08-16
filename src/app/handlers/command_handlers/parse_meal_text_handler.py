"""
Handler for parsing natural language meal text into structured food items.
"""

import asyncio
import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from src.app.commands.meal.parse_meal_text_command import ParseMealTextCommand
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.meal_text_parsing_utils import (
    extract_json_from_response,
    parse_fatsecret_nutrition,
)
from src.app.schemas.meal_schemas import ParsedFoodItemDto, ParseMealTextResponseDto
from src.domain.exceptions.ai_exceptions import AIOutputValidationError
from src.domain.model.ai.nutrition_contracts import MealTextNutritionResponse
from src.domain.model.nutrition.macros import Macros
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.ai_output_validation_service import (
    build_validation_retry_prompt,
    validate_ai_output,
)
from src.domain.services.emoji_validator import validate_emoji
from src.domain.services.nutrition_calculation_service import (
    _convert_with_allowed_units,
    clamp_nutrition_values,
    convert_quantity_to_grams,
    normalize_unit_for_manual_save,
    scale_per_100g_nutrition,
)
from src.domain.services.nutrition_integrity_policy import (
    NUTRITION_INTEGRITY_POLICY_VERSION,
    normalize_serving_options,
)
from src.domain.services.nutrition_resolver import (
    normalize_food_lookup_name,
    preparation_matches,
    select_nutrition_candidate,
    validate_ai_fallback,
    validate_reference_candidate,
)
from src.domain.services.prompts.input_sanitizer import (
    sanitize_user_description,
    validate_refinement_items,
)
from src.domain.services.prompts.system_prompts import SystemPrompts
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)

logger = logging.getLogger(__name__)
PARSE_TEXT_VALIDATION_PURPOSE = "parse_text"
MAX_VALIDATION_ATTEMPTS = 2
MAX_PROVIDER_SEARCHES = 5
MAX_PROVIDER_DETAILS = 5
MAX_PROVIDER_CONCURRENCY = 3
TRUSTED_QUANTITY_UNITS = {
    "g",
    "gram",
    "grams",
    "kg",
    "kilogram",
    "kilograms",
    "ml",
    "l",
    "liter",
    "litre",
    "piece",
    "pieces",
    "slice",
    "slices",
    "cup",
    "cups",
    "tablespoon",
    "tablespoons",
    "tbsp",
    "teaspoon",
    "teaspoons",
    "tsp",
    "serving",
    "portion",
}


@dataclass
class _ParseTextRequestBudget:
    """Request-wide limits shared by AI and staged reference resolution."""

    deadline: float | None = None
    ai_generations: int = 0
    provider_searches: int = 0
    provider_details: int = 0
    semaphore: asyncio.Semaphore = field(
        default_factory=lambda: asyncio.Semaphore(MAX_PROVIDER_CONCURRENCY)
    )


def _parse_text_fatsecret_timeout_seconds() -> float:
    try:
        return max(0.01, float(os.getenv("PARSE_TEXT_FATSECRET_TIMEOUT_SECONDS", "3")))
    except ValueError:
        return 3.0


@handles(ParseMealTextCommand)
class ParseMealTextHandler(
    EventHandler[ParseMealTextCommand, ParseMealTextResponseDto]
):
    """Handler for parsing meal text descriptions using AI."""

    def __init__(
        self,
        meal_generation_service: MealGenerationServicePort,
        fat_secret_service: Any | None = None,
        translation_service: DeepLTextTranslationService | None = None,
        food_reference_batch_lookup: Any | None = None,
        structured_reference_enabled: bool = True,
    ):
        self._meal_generation_service = meal_generation_service
        self._fat_secret_service = fat_secret_service
        self._translation_service = translation_service
        self._food_reference_batch_lookup = food_reference_batch_lookup
        self._structured_reference_enabled = structured_reference_enabled

    async def handle(self, command: ParseMealTextCommand) -> ParseMealTextResponseDto:
        # Sanitize user input
        sanitized_text = sanitize_user_description(command.text)
        if not sanitized_text:
            raise ValueError("Invalid or empty meal description.")
        validated_current_items = validate_refinement_items(command.current_items)

        # Add refinement context if current_items provided
        if validated_current_items:
            context = json.dumps(validated_current_items, ensure_ascii=False)
            sanitized_text += (
                f"\n\nCurrent meal items:\n{context}\n\n"
                "Update the meal based on my request above. Return the COMPLETE updated list."
            )

        # Build messages with locale-aware food names
        system_prompt = SystemPrompts.get_meal_text_parsing_prompt(
            language=command.language
        )

        budget = _ParseTextRequestBudget()
        semantic_feedback: list[str] = []
        enhanced_items: list[dict[str, Any]] = []
        validated_payload: dict[str, Any] | None = None
        for semantic_attempt in range(2):
            retry_prompt = sanitized_text
            if semantic_feedback:
                retry_prompt += (
                    "\n\nValidation feedback (fix the whole response): "
                    + "; ".join(semantic_feedback[:4])
                )
            validated_payload, raw_payload = await self._generate_parse_text_payload(
                prompt=retry_prompt,
                system_prompt=system_prompt,
                budget=budget,
            )
            emoji = validate_emoji(validated_payload.get("emoji"))
            parsed_items = self._to_flat_parse_text_items(
                validated_payload, raw_payload
            )
            if budget.deadline is None:
                budget.deadline = (
                    time.monotonic() + _parse_text_fatsecret_timeout_seconds()
                )
            local_references = await self._find_local_references(parsed_items, budget)
            try:
                enhanced_items = [
                    await self._cascade_lookup(
                        item,
                        budget=budget,
                        local_reference=local_references.get(
                            normalize_food_lookup_name(
                                item.get("lookup_name") or item.get("name", "")
                            )
                        ),
                    )
                    for item in parsed_items
                ]
                break
            except AIOutputValidationError as exc:
                if semantic_attempt >= 1 or budget.ai_generations >= 2:
                    raise
                semantic_feedback = list(
                    exc.validation_details or ["nutrition fallback failed"]
                )
        else:
            raise AIOutputValidationError(
                "Invalid AI nutrition output",
                purpose=PARSE_TEXT_VALIDATION_PURPOSE,
                attempt_count=budget.ai_generations,
                validation_details=semantic_feedback,
            )

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
                fiber=item.get("fiber", 0),
                sugar=item.get("sugar", 0),
                data_source=item.get("data_source"),
                fdc_id=item.get("fdc_id"),
                allowed_units=item.get("allowed_units") or [],
                food_id=item.get("food_id"),
                food_reference_id=item.get("food_reference_id"),
                origin=item.get("origin"),
                source_namespace=item.get("source_namespace"),
                source_food_id=item.get("source_food_id"),
                nutrition_basis=item.get("nutrition_basis"),
                nutrition_contract_version=item.get("nutrition_contract_version"),
                calories_per_100g=item.get("calories_per_100g"),
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
        self,
        *,
        prompt: str,
        system_prompt: str,
        budget: _ParseTextRequestBudget | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        retry_system_prompt = system_prompt
        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            if budget is not None:
                if budget.ai_generations >= 2:
                    raise AIOutputValidationError(
                        "AI generation budget exhausted",
                        purpose=PARSE_TEXT_VALIDATION_PURPOSE,
                        attempt_count=budget.ai_generations,
                        validation_details=["ai_generation_budget_exhausted"],
                    )
                budget.ai_generations += 1
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
                    "[AI-OUTPUT-VALIDATION-FAILED] purpose=%s attempt=%s details=%s",
                    PARSE_TEXT_VALIDATION_PURPOSE,
                    attempt,
                    exc.validation_details,
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
        self, validated_payload: dict[str, Any], _raw_payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        flat_items = []
        for item in validated_payload.get("items", []):
            macros = item.get("macros", {})
            flat_item = {
                "name": item.get("name"),
                "lookup_name": item.get("lookup_name")
                or self._extract_english_name(item.get("name", "")),
                "preparation": item.get("preparation", "unknown"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "english_unit": item.get("english_unit"),
                "protein": macros.get("protein_g", 0.0),
                "carbs": macros.get("carbs_g", 0.0),
                "fat": macros.get("fat_g", 0.0),
                "fiber": macros.get("fiber_g", 0.0),
                "sugar": macros.get("sugar_g", 0.0),
                "calories": self._derive_calories_from_macros(macros),
            }
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

    async def _find_local_references(
        self,
        items: list[dict[str, Any]],
        budget: _ParseTextRequestBudget,
    ) -> dict[str, dict[str, Any]]:
        if not self._food_reference_batch_lookup:
            return {}
        names = sorted(
            {
                normalize_food_lookup_name(
                    item.get("lookup_name") or item.get("name", "")
                )
                for item in items
            }
            - {""}
        )
        deadline = budget.deadline
        if not names or deadline is None or time.monotonic() >= deadline:
            return {}
        try:
            remaining = max(0.01, deadline - time.monotonic())
            return await asyncio.wait_for(
                self._food_reference_batch_lookup(names), timeout=remaining
            )
        except Exception as exc:
            logger.debug(
                "parse_text local reference lookup failed: %s", type(exc).__name__
            )
            return {}

    async def _cascade_lookup(
        self,
        item: dict[str, Any],
        *,
        budget: _ParseTextRequestBudget,
        local_reference: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve local reference, one staged provider detail, then safe AI fallback."""
        name = str(item.get("name") or "")
        lookup_name = str(item.get("lookup_name") or self._extract_english_name(name))
        preparation = str(item.get("preparation") or "unknown")
        quantity = float(item.get("quantity") or 1.0)
        unit = item.get("english_unit") or item.get("unit", "serving")
        quantity_g = self._quantity_in_grams(item, lookup_name)
        fallback_quantity_g = self._trusted_quantity_in_grams(item, lookup_name)

        if local_reference and self._local_reference_is_usable(
            local_reference, lookup_name, preparation
        ):
            candidate = validate_reference_candidate(
                local_reference,
                require_energy=False,
                require_metric_basis=False,
            )
            if candidate:
                return self._apply_reference(
                    item, candidate, quantity_g, "local_reference", local_reference
                )

        if self._fat_secret_service and self._structured_reference_enabled:
            structured = await self._resolve_staged_provider(
                item, lookup_name, preparation, quantity_g, budget
            )
            if structured is not None:
                return structured
        elif self._fat_secret_service:
            legacy = await self._resolve_legacy_provider(
                item, lookup_name, quantity, unit, budget
            )
            if legacy is not None:
                return legacy

        # When the user specified an explicit gram-weight quantity, the AI may have
        # produced nutrition values for a standard serving rather than scaling them
        # to the actual weight.  Rescale the macros proportionally so that a tiny
        # quantity (e.g. "0.5 gram rau sống") does not fail the density check.
        raw_unit = str(item.get("english_unit") or item.get("unit") or "").lower().strip()
        if raw_unit in {"g", "gram", "grams", "kg", "kilogram", "kilograms"} and fallback_quantity_g:
            item = self._scale_ai_macros_to_quantity_g(item, fallback_quantity_g)

        if not validate_ai_fallback(
            name=lookup_name,
            protein=item.get("protein", 0),
            carbs=item.get("carbs", 0),
            fat=item.get("fat", 0),
            fiber=item.get("fiber", 0),
            quantity_g=fallback_quantity_g,
        ):
            raise AIOutputValidationError(
                "AI nutrition fallback failed physical validation",
                purpose=PARSE_TEXT_VALIDATION_PURPOSE,
                attempt_count=1,
                validation_details=["unsafe_density_fallback"],
            )
        item["data_source"] = "ai_estimate"
        return item

    async def _resolve_staged_provider(
        self,
        item: dict[str, Any],
        lookup_name: str,
        preparation: str,
        quantity_g: float,
        budget: _ParseTextRequestBudget,
    ) -> dict[str, Any] | None:
        provider = self._fat_secret_service
        if provider is None:
            return None
        if not hasattr(provider, "search_food_candidates"):
            return await self._resolve_legacy_provider(
                item,
                lookup_name,
                float(item.get("quantity") or 1),
                item.get("english_unit") or item.get("unit", "serving"),
                budget,
            )
        if budget.provider_searches >= MAX_PROVIDER_SEARCHES:
            return None
        budget.provider_searches += 1
        candidates = await self._provider_call(
            lambda: provider.search_food_candidates(lookup_name, max_results=5),
            budget,
        )
        if candidates is None:
            return None
        selected = select_nutrition_candidate(candidates, lookup_name, preparation)
        if not selected or not selected.get("food_id"):
            return None
        if budget.provider_details >= MAX_PROVIDER_DETAILS:
            return None
        budget.provider_details += 1
        details = await self._provider_call(
            lambda: provider.get_food_details(str(selected["food_id"])),
            budget,
        )
        if not isinstance(details, dict):
            return None
        merged = {**selected, **details}
        candidate = validate_reference_candidate(merged)
        if candidate is None:
            return None
        return self._apply_reference(item, candidate, quantity_g, "fatsecret", merged)

    async def _resolve_legacy_provider(
        self,
        item: dict[str, Any],
        lookup_name: str,
        quantity: float,
        unit: str,
        budget: _ParseTextRequestBudget,
    ) -> dict[str, Any] | None:
        provider = self._fat_secret_service
        if provider is None:
            return None
        if budget.provider_searches >= MAX_PROVIDER_SEARCHES:
            return None
        budget.provider_searches += 1
        try:
            results = await self._provider_call(
                lambda: provider.search_foods(lookup_name, max_results=5),
                budget,
            )
        except Exception as exc:
            logger.debug("parse_text legacy provider failed: %s", type(exc).__name__)
            return None
        if not results:
            return None
        selected = select_nutrition_candidate(results, lookup_name)
        if selected is None:
            return None
        if not self._reference_identity(selected, "fatsecret")["source_food_id"]:
            return None
        structured = validate_reference_candidate(selected, require_energy=False)
        per_100g = (
            {
                "calories_100g": selected.get("calories_100g"),
                "protein_100g": selected.get("protein_100g"),
                "carbs_100g": selected.get("carbs_100g"),
                "fat_100g": selected.get("fat_100g"),
                "fiber_100g": selected.get("fiber_100g", 0),
                "sugar_100g": selected.get("sugar_100g", 0),
            }
            if structured
            else parse_fatsecret_nutrition(selected)
        )
        if not per_100g:
            return None
        allowed_units = self._safe_allowed_units(selected.get("allowed_units"))
        quantity_g = self._canonicalize_reference_quantity(
            item,
            quantity_g=self._quantity_in_grams(item, lookup_name),
            allowed_units=allowed_units,
        )
        scaled = scale_per_100g_nutrition(
            {
                "calories": per_100g.get("calories_100g", per_100g.get("calories", 0)),
                "protein": per_100g.get("protein_100g", per_100g.get("protein", 0)),
                "carbs": per_100g.get("carbs_100g", per_100g.get("carbs", 0)),
                "fat": per_100g.get("fat_100g", per_100g.get("fat", 0)),
                "fiber": per_100g.get("fiber_100g", per_100g.get("fiber", 0)),
                "sugar": per_100g.get("sugar_100g", per_100g.get("sugar", 0)),
            },
            item["quantity"],
            item["unit"],
            allowed_units=allowed_units,
            food_name=lookup_name,
            strict_allowed_units=True,
        )
        if not validate_ai_fallback(
            name=lookup_name,
            protein=scaled.get("protein"),
            carbs=scaled.get("carbs"),
            fat=scaled.get("fat"),
            fiber=scaled.get("fiber"),
            quantity_g=quantity_g,
        ):
            return None
        item.update(scaled)
        item["calories"] = self._derive_calories_from_macros(item)
        item["allowed_units"] = allowed_units
        item["data_source"] = "fatsecret"
        item.update(self._reference_identity(selected, "fatsecret"))
        item["nutrition_basis"] = "100g"
        item["nutrition_contract_version"] = NUTRITION_INTEGRITY_POLICY_VERSION
        item["calories_per_100g"] = self._derive_calories_from_macros(
            {
                "protein_g": per_100g.get("protein_100g", per_100g.get("protein", 0)),
                "carbs_g": per_100g.get("carbs_100g", per_100g.get("carbs", 0)),
                "fat_g": per_100g.get("fat_100g", per_100g.get("fat", 0)),
                "fiber_g": per_100g.get("fiber_100g", per_100g.get("fiber", 0)),
            }
        )
        return item

    async def _provider_call(
        self,
        awaitable_factory: Callable[[], Awaitable[Any]],
        budget: _ParseTextRequestBudget,
    ) -> Any:
        deadline = budget.deadline
        if deadline is None:
            return None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        async with budget.semaphore:
            deadline = budget.deadline
            if deadline is None:
                return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                return await asyncio.wait_for(awaitable_factory(), timeout=remaining)
            except Exception as exc:
                logger.debug("parse_text provider call failed: %s", type(exc).__name__)
                return None

    def _quantity_in_grams(self, item: dict[str, Any], food_name: str) -> float:
        if item.get("quantity_g") is not None:
            return float(item["quantity_g"])
        quantity = float(item.get("quantity") or 1)
        unit = item.get("english_unit") or item.get("unit", "serving")
        return convert_quantity_to_grams(
            quantity, normalize_unit_for_manual_save(unit), food_name
        )

    def _scale_ai_macros_to_quantity_g(
        self, item: dict[str, Any], quantity_g: float
    ) -> dict[str, Any]:
        """Proportionally scale AI-estimated macros to fit within the physical weight.

        The LLM sometimes returns per-serving nutrition values regardless of the
        user's specified gram quantity.  When the sum of macros (protein + carbs +
        fat + fiber) exceeds the actual weight we infer an implied serving size and
        scale all macro fields down to the real quantity.
        """
        protein = float(item.get("protein") or 0)
        carbs = float(item.get("carbs") or 0)
        fat = float(item.get("fat") or 0)
        fiber = float(item.get("fiber") or 0)
        implied_serving_g = protein + carbs + fat + fiber
        if implied_serving_g <= quantity_g * 1.1 or implied_serving_g <= 0:
            # Macros already fit within the physical weight – nothing to do.
            return item
        factor = quantity_g / implied_serving_g
        item = dict(item)
        item["protein"] = round(protein * factor, 2)
        item["carbs"] = round(carbs * factor, 2)
        item["fat"] = round(fat * factor, 2)
        item["fiber"] = round(fiber * factor, 2)
        if item.get("sugar") is not None:
            item["sugar"] = round(float(item["sugar"]) * factor, 2)
        # Keep calories consistent with the scaled macros.
        item["calories"] = self._derive_calories_from_macros(item)
        return item

    def _trusted_quantity_in_grams(
        self, item: dict[str, Any], food_name: str
    ) -> float | None:
        """Return grams only when the input supplies a reliable unit basis."""
        if item.get("quantity_g") is not None:
            return self._quantity_in_grams(item, food_name)
        raw_unit = str(item.get("english_unit") or item.get("unit") or "")
        unit = raw_unit.lower().strip().split(",", 1)[0].split(" ", 1)[0]
        if unit not in TRUSTED_QUANTITY_UNITS:
            return None
        return self._quantity_in_grams(item, food_name)

    def _local_reference_is_usable(
        self, reference: dict[str, Any], lookup_name: str, preparation: str
    ) -> bool:
        if not reference.get("is_verified"):
            return False
        source = str(reference.get("source") or "").lower()
        if source not in {
            "usda",
            "usda_fdc",
            "fooddata_central",
            "fatsecret",
            "food_reference",
            "seed",
            "catalog_seed",
            "nin",
        }:
            return False
        return preparation_matches(
            str(reference.get("name") or lookup_name), preparation
        )

    def _apply_reference(
        self,
        item: dict[str, Any],
        candidate: Any,
        quantity_g: float,
        source: str,
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        allowed_units = self._safe_allowed_units(
            raw.get("allowed_units") or raw.get("serving_sizes")
        )
        if not allowed_units:
            allowed_units = list(candidate.allowed_units or [])
        quantity_g = self._canonicalize_reference_quantity(
            item,
            quantity_g=quantity_g,
            allowed_units=allowed_units,
        )
        factor = quantity_g / 100.0
        item.update(
            {
                "protein": round(candidate.protein_per_100g * factor, 2),
                "carbs": round(candidate.carbs_per_100g * factor, 2),
                "fat": round(candidate.fat_per_100g * factor, 2),
                "fiber": round(candidate.fiber_per_100g * factor, 2),
                "sugar": round(candidate.sugar_per_100g * factor, 2),
            }
        )
        item["calories"] = self._derive_calories_from_macros(item)
        item["data_source"] = (
            "fatsecret"
            if source == "fatsecret"
            or str(raw.get("source", "")).lower() == "fatsecret"
            else "usda"
        )
        item["fdc_id"] = raw.get("fdc_id")
        item.update(self._reference_identity(raw, source))
        item["nutrition_basis"] = "100g"
        item["nutrition_contract_version"] = NUTRITION_INTEGRITY_POLICY_VERSION
        item["calories_per_100g"] = self._derive_calories_from_macros(
            {
                "protein_g": candidate.protein_per_100g,
                "carbs_g": candidate.carbs_per_100g,
                "fat_g": candidate.fat_per_100g,
                "fiber_g": candidate.fiber_per_100g,
            }
        )
        item["allowed_units"] = allowed_units
        return item

    @staticmethod
    def _canonicalize_reference_quantity(
        item: dict[str, Any],
        *,
        quantity_g: float,
        allowed_units: list[dict[str, Any]],
    ) -> float:
        """Keep parsed portions saveable against the same source snapshot."""
        quantity = float(item.get("quantity") or 1.0)
        source_unit = str(item.get("english_unit") or item.get("unit") or "g")
        try:
            authoritative_grams = _convert_with_allowed_units(
                quantity,
                source_unit,
                allowed_units,
                str(item.get("lookup_name") or item.get("name") or ""),
                strict=True,
            )
        except ValueError:
            item["quantity"] = quantity_g
            item["unit"] = "g"
            item["english_unit"] = "g"
            item["quantity_g"] = quantity_g
            return quantity_g

        item["unit"] = source_unit
        item["english_unit"] = source_unit
        item["quantity_g"] = authoritative_grams
        return authoritative_grams

    @staticmethod
    def _reference_identity(raw: dict[str, Any], source: str) -> dict[str, Any]:
        raw_source = str(raw.get("source") or source or "").lower()
        if (
            source == "local_reference"
            or raw_source == "food_reference"
            or raw.get("food_reference_id") is not None
        ):
            reference_id = raw.get("food_reference_id") or raw.get("id")
            return {
                "origin": "local",
                "food_reference_id": reference_id,
                "food_id": f"food_reference:{reference_id}",
                "source_namespace": "food_reference",
                "source_food_id": str(reference_id),
            }
        if raw.get("fdc_id") is not None or raw.get("fdcId") is not None:
            fdc_id = raw.get("fdc_id") or raw.get("fdcId")
            return {
                "origin": "usda",
                "food_id": f"usda_fdc:{fdc_id}",
                "source_namespace": "usda_fdc",
                "source_food_id": str(fdc_id),
            }
        namespace = str(raw.get("source_namespace") or raw_source or "fatsecret")
        source_id = str(raw.get("source_food_id") or raw.get("food_id") or "")
        if source_id.startswith(f"{namespace}:"):
            source_id = source_id[len(namespace) + 1 :]
        if not source_id:
            return {
                "origin": "provider",
                "food_id": None,
                "source_namespace": namespace,
                "source_food_id": None,
            }
        return {
            "origin": "provider",
            "food_id": f"{namespace}:{source_id}",
            "source_namespace": namespace,
            "source_food_id": source_id,
        }

    @staticmethod
    def _safe_allowed_units(raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        units: list[dict[str, Any]] = []
        for entry in raw[:12]:
            if not isinstance(entry, dict):
                continue
            unit = str(entry.get("unit") or entry.get("name") or "").strip()
            description = str(entry.get("description") or "").strip()
            raw_gram_weight = entry.get("gram_weight") or entry.get("grams")
            if raw_gram_weight is None:
                continue
            try:
                gram_weight = float(raw_gram_weight)
            except (TypeError, ValueError):
                continue
            if (
                not unit
                or len(unit) > 100
                or len(description) > 100
                or not gram_weight > 0
                or not all(ord(char) >= 32 for char in unit + description)
            ):
                continue
            units.append(
                {
                    "unit": unit,
                    "gram_weight": gram_weight,
                    "description": description,
                }
            )
        return normalize_serving_options(units, provider_100g_label=True) or []

    @staticmethod
    def _is_english(name: str) -> bool:
        """Check if name is likely English (ASCII-only, ignoring digits/punct)."""
        letters = [c for c in name if c.isalpha()]
        return bool(letters) and all(ord(c) < 128 for c in letters)

    async def _translate_english_names_deepl(
        self, items: list[dict[str, Any]], language: str
    ) -> None:
        """Detect and batch-translate any remaining English food names using DeepL."""
        if self._translation_service is None:
            return

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
        except Exception as exc:
            logger.warning(
                "DeepL name translation failed, keeping English: %s",
                type(exc).__name__,
            )

    @staticmethod
    def _extract_english_name(name: str) -> str:
        """Extract English name for fatsecret lookup.

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
