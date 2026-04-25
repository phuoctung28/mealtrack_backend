"""
DeepL-backed meal translation service.

Translates dish_name, instructions, and ingredient names for a meal using DeepL.
Checks the meal_translation table first; only calls the DeepL API when a fully-
cached translation does not yet exist.
"""

import logging
from typing import List, Optional

from src.domain.model.meal import Meal, MealTranslation
from src.domain.model.nutrition import FoodItem
from src.domain.ports.deepl_translation_port import DeepLTranslationPort
from src.domain.ports.meal_translation_repository_port import (
    MealTranslationRepositoryPort,
)
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class DeepLMealTranslationService:
    """
    Translates meal content (name, instructions, ingredients) via DeepL.

    Caching strategy
    ----------------
    A translation row is considered fully cached when all three of
    dish_name, meal_instruction, and meal_ingredients are non-None.
    If a cached row exists, the DeepL API is not called.
    If no row exists or the row is partially cached, DeepL is called and
    the result is upserted.

    On any error the method logs a warning and returns None so the caller
    can fall back to English without blocking the meal response.
    """

    def __init__(
        self,
        translation_repo: MealTranslationRepositoryPort,
        deepl_port: DeepLTranslationPort,
    ) -> None:
        self._repo = translation_repo
        self._deepl = deepl_port

    async def translate_meal(
        self,
        meal: Meal,
        dish_name: str,
        food_items: List[FoodItem],
        target_language: str,
        instructions: Optional[list] = None,
    ) -> Optional[MealTranslation]:
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
            existing = self._repo.get_by_meal_and_language(
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
            normalised_steps: List[dict] = []
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

            translated = await self._deepl.translate_texts(
                strings_to_translate, target_language
            )

            # Pad result to the expected length in case DeepL returns fewer items.
            while len(translated) < len(strings_to_translate):
                translated.append(strings_to_translate[len(translated)])

            # --- Unpack results ---
            translated_dish_name = translated[0]

            n = len(ingredient_names)
            translated_ingredients = translated[1 : 1 + n]

            m = len(instruction_texts)
            translated_instruction_texts = translated[1 + n : 1 + n + m]

            translated_instruction_list: Optional[list] = None
            if normalised_steps:
                translated_instruction_list = []
                for orig_step, trans_text in zip(
                    normalised_steps, translated_instruction_texts
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
                food_items=[],  # Ingredients stored in meal_ingredients, not child table
                meal_instruction=translated_instruction_list,
                meal_ingredients=translated_ingredients,
                translated_at=utc_now(),
            )

            saved = self._repo.save(translation)
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
