"""Persisted meal translation orchestration."""

import asyncio
import inspect
import logging
from typing import Any, cast

from src.domain.model.meal import FoodItemTranslation, Meal, MealTranslation
from src.domain.model.nutrition import FoodItem
from src.domain.model.translation_result import TranslationOutcome, TranslationResult
from src.domain.ports.meal_translation_repository_port import (
    MealTranslationRepositoryPort,
)
from src.domain.services.translation.text_translation_service import (
    TextTranslationService,
)
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class MealTranslationService:
    """Translate meal content and persist only complete provider results."""

    def __init__(
        self,
        translation_repo: MealTranslationRepositoryPort,
        text_translation_service: TextTranslationService,
    ) -> None:
        self._repo = translation_repo
        self._text_service = text_translation_service

    async def translate_meal(
        self,
        meal: Meal,
        dish_name: str,
        food_items: list[FoodItem],
        target_language: str,
        instructions: list | None = None,
    ) -> MealTranslation | None:
        """
        Translate a meal to target_language.

        Args:
            meal: Meal domain model (only meal_id is used).
            dish_name: English dish name.
            food_items: Food items whose names will be translated.
            target_language: ISO 639-1 target language code.
            instructions: Optional list of instruction dicts or strings.

        Returns:
            Saved MealTranslation or None on skip / failure.
        """
        if target_language == "en":
            return None

        try:
            # --- Cache check ---
            existing = await self._get_by_meal_and_language(
                meal.meal_id, target_language
            )
            if existing and existing.is_fully_cached(
                expected_ingredient_count=len(
                    [item for item in food_items if item.name]
                ),
                expected_instruction_count=len(instructions or []),
            ):
                logger.debug(
                    "Translation cache hit: meal=%s lang=%s",
                    meal.meal_id,
                    target_language,
                )
                return existing

            # --- Normalise instructions to List[dict] ---
            normalised_steps: list[dict] = []
            if instructions:
                for step in instructions:
                    if isinstance(step, dict):
                        normalised_steps.append(step)
                    elif isinstance(step, str):
                        normalised_steps.append(
                            {"instruction": step, "duration_minutes": None}
                        )

            ingredient_names = [item.name for item in food_items if item.name]
            instruction_texts = [s.get("instruction", "") for s in normalised_steps]

            # Build a single flat list so we use one provider call.
            # Layout: [dish_name, *ingredient_names, *instruction_texts]
            strings_to_translate = [dish_name] + ingredient_names + instruction_texts

            result = await _translate_texts(
                self._text_service, strings_to_translate, target_language
            )
            translated = result.to_list()
            if result.outcome is not TranslationOutcome.TRANSLATED:
                translated.extend(strings_to_translate[len(translated) :])

            # --- Unpack results ---
            translated_dish_name = translated[0]

            n = len(ingredient_names)
            translated_ingredients = translated[1 : 1 + n]
            translated_food_items = [
                FoodItemTranslation(
                    food_item_id=str(item.id),
                    name=translated_name,
                )
                for item, translated_name in zip(
                    food_items, translated_ingredients, strict=False
                )
                if item.name
            ]

            m = len(instruction_texts)
            translated_instruction_texts = translated[1 + n : 1 + n + m]

            translated_instruction_list: list | None = None
            if normalised_steps:
                translated_instruction_list = []
                for orig_step, trans_text in zip(
                    normalised_steps, translated_instruction_texts, strict=False
                ):
                    translated_instruction_list.append(
                        {
                            "instruction": trans_text,
                            "duration_minutes": orig_step.get("duration_minutes"),
                        }
                    )

            translation = MealTranslation(
                meal_id=meal.meal_id,
                language=target_language,
                dish_name=translated_dish_name,
                food_items=translated_food_items,
                meal_instruction=translated_instruction_list,
                meal_ingredients=translated_ingredients,
                translated_at=utc_now(),
            )

            if result.outcome is not TranslationOutcome.TRANSLATED:
                return translation
            saved = await self._save(translation)
            logger.info(
                "Meal translation saved meal=%s lang=%s", meal.meal_id, target_language
            )
            return saved

        except Exception as exc:
            logger.warning(
                "Meal translation failed for meal=%s lang=%s error_type=%s",
                meal.meal_id,
                target_language,
                type(exc).__name__,
            )
            return None

    async def _get_by_meal_and_language(
        self, meal_id: str, language: str
    ) -> MealTranslation | None:
        method = self._repo.get_by_meal_and_language
        if inspect.iscoroutinefunction(method):
            return await cast(Any, method)(meal_id, language)
        return await asyncio.to_thread(cast(Any, method), meal_id, language)

    async def _save(self, translation: MealTranslation) -> MealTranslation:
        method = self._repo.save
        if inspect.iscoroutinefunction(method):
            return await cast(Any, method)(translation)
        return await asyncio.to_thread(cast(Any, method), translation)


async def _translate_texts(
    service: TextTranslationService, texts: list[str], target_language: str
) -> TranslationResult:
    """Translate an ordered batch from the canonical English source."""
    return await service.translate_texts(texts, "en", target_language)
