"""
DeepL-backed meal translation service.

Translates dish_name, instructions, and ingredient names for a meal using DeepL.
Uses the core DeepLTextTranslationService internally for actual API calls.
Checks the meal_translation table first; only calls DeepL when a fully-
cached translation does not yet exist.
"""

import asyncio
import inspect
import logging

from src.domain.model.meal import FoodItemTranslation, Meal, MealTranslation
from src.domain.model.nutrition import FoodItem
from src.domain.ports.meal_translation_repository_port import (
    MealTranslationRepositoryPort,
)
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class DeepLMealTranslationService:
    """
    Translates meal content (name, instructions, ingredients) via DeepL.

    Uses DeepLTextTranslationService for actual translation calls.
    Adds meal-specific caching logic on top.
    """

    def __init__(
        self,
        translation_repo: MealTranslationRepositoryPort,
        text_translation_service: DeepLTextTranslationService,
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
            if existing and existing.is_fully_cached():
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

            # Build a single flat list so we use ONE DeepL API call.
            # Layout: [dish_name, *ingredient_names, *instruction_texts]
            strings_to_translate = [dish_name] + ingredient_names + instruction_texts

            translated = await self._text_service.translate_texts(
                strings_to_translate, target_language
            )

            # Pad result to the expected length in case DeepL returns fewer items.
            while len(translated) < len(strings_to_translate):
                translated.append(strings_to_translate[len(translated)])

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

            saved = await self._save(translation)
            logger.info(
                "DeepL translation saved: meal=%s lang=%s dish='%s'",
                meal.meal_id,
                target_language,
                translated_dish_name,
            )
            return saved

        except Exception as exc:
            logger.warning(
                "DeepL translation failed for meal=%s lang=%s: %s",
                meal.meal_id,
                target_language,
                exc,
            )
            return None

    async def _get_by_meal_and_language(
        self, meal_id: str, language: str
    ) -> MealTranslation | None:
        method = self._repo.get_by_meal_and_language
        if inspect.iscoroutinefunction(method):
            return await method(meal_id, language)
        return await asyncio.to_thread(method, meal_id, language)

    async def _save(self, translation: MealTranslation) -> MealTranslation:
        method = self._repo.save
        if inspect.iscoroutinefunction(method):
            return await method(translation)
        return await asyncio.to_thread(method, translation)
