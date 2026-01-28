"""
Meal analysis translation service.

Translates meal analysis results (dish name and food items) to target language.
Reuses existing TranslationService._batch_translate() for batch translation.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from src.domain.model.meal import Meal, MealTranslation, FoodItemTranslation
from src.domain.model.nutrition import FoodItem
from src.domain.ports.meal_translation_repository_port import MealTranslationRepositoryPort
from src.domain.services.meal_suggestion.translation_service import TranslationService

logger = logging.getLogger(__name__)


class MealAnalysisTranslationService:
    """
    Translates meal analysis results using existing TranslationService.

    Translates:
    - dish_name at meal level
    - name and description at food item level

    Features:
    - Skips translation for English (en)
    - Retry failed items once before fallback to original
    - Max ~3s additional latency
    """

    def __init__(
        self,
        translation_repo: MealTranslationRepositoryPort,
        translation_service: TranslationService
    ):
        """
        Initialize the service.

        Args:
            translation_repo: Repository for persisting translations
            translation_service: Existing TranslationService for batch translation
        """
        self._repo = translation_repo
        self._translator = translation_service

    async def translate_meal(
        self,
        meal: Meal,
        dish_name: str,
        food_items: List[FoodItem],
        target_language: str
    ) -> Optional[MealTranslation]:
        """
        Translate meal content to target language.

        Args:
            meal: The meal being analyzed
            dish_name: Original English dish name
            food_items: List of food items with names/descriptions
            target_language: ISO 639-1 language code

        Returns:
            MealTranslation if successful, None if English or failed
        """
        # Skip if English
        if target_language == "en":
            logger.debug(f"Skipping translation for English")
            return None

        # Skip if no food items
        if not food_items:
            logger.debug(f"No food items to translate")
            return None

        try:
            # Extract strings to translate
            strings, paths = self._extract_translatable_strings(dish_name, food_items)

            if not strings:
                logger.warning(f"No translatable strings found")
                return None

            # Batch translate with retry logic
            translated_strings = await self._translate_with_retry(strings, target_language)

            # Build MealTranslation domain model
            translation = self._build_translation(
                meal.meal_id,
                dish_name,
                food_items,
                translated_strings,
                paths,
                target_language
            )

            # Persist to database
            saved_translation = self._repo.save(translation)

            logger.info(
                f"Translated meal {meal.meal_id} to {target_language}: "
                f"{len(strings)} strings, dish='{dish_name}' -> '{saved_translation.dish_name}'"
            )

            return saved_translation

        except Exception as e:
            logger.error(f"Translation failed for meal {meal.meal_id}: {e}")
            return None

    def _extract_translatable_strings(
        self,
        dish_name: str,
        food_items: List[FoodItem]
    ) -> Tuple[List[str], List[str]]:
        """
        Extract strings to translate with their paths.

        Returns:
            Tuple of (strings, paths) lists
        """
        strings = []
        paths = []

        # Add dish name
        if dish_name:
            strings.append(dish_name)
            paths.append("dish_name")

        # Add food item names and descriptions
        for i, item in enumerate(food_items):
            if item.name:
                strings.append(item.name)
                paths.append(f"food_items[{i}].name")
            # FoodItem may have optional description attribute
            description = getattr(item, 'description', None)
            if description:
                strings.append(description)
                paths.append(f"food_items[{i}].description")

        return strings, paths

    async def _translate_with_retry(
        self,
        strings: List[str],
        target_language: str
    ) -> List[str]:
        """
        Translate strings with one retry for failed items.

        Args:
            strings: List of strings to translate
            target_language: Target language code

        Returns:
            List of translated strings (or original on final failure)
        """
        # First attempt
        results = await self._translator._batch_translate(strings, target_language)

        # Identify failures (empty or None results)
        failed_indices = [
            i for i, r in enumerate(results)
            if not r or not r.strip()
        ]

        if not failed_indices:
            return results

        # Retry failed items once
        failed_strings = [strings[i] for i in failed_indices]
        retry_results = await self._translator._batch_translate(
            failed_strings, target_language
        )

        # Merge: use retry results for failures, original for success
        for i, retry_result in zip(failed_indices, retry_results):
            if retry_result and retry_result.strip():
                results[i] = retry_result
            else:
                # Retry also failed, keep original
                results[i] = strings[i]
                logger.warning(f"Translation failed after retry, using original: {strings[i][:50]}...")

        return results

    def _build_translation(
        self,
        meal_id: str,
        dish_name: str,
        food_items: List[FoodItem],
        translated_strings: List[str],
        paths: List[str],
        language: str
    ) -> MealTranslation:
        """
        Build MealTranslation domain model from translated strings.

        Args:
            meal_id: The meal ID
            dish_name: Original English dish name
            food_items: Original food items
            translated_strings: Translated strings in same order as extraction
            paths: Paths corresponding to each string
            language: Target language code

        Returns:
            MealTranslation domain model
        """
        # Build mapping from path to translated string
        translation_map = dict(zip(paths, translated_strings))

        # Get translated dish name
        translated_dish_name = translation_map.get("dish_name", dish_name)

        # Build food item translations
        food_item_translations = []
        food_item_index = 0

        for item in food_items:
            name_path = f"food_items[{food_item_index}].name"
            desc_path = f"food_items[{food_item_index}].description"

            translated_name = translation_map.get(name_path, item.name)
            # FoodItem may have optional description attribute
            original_desc = getattr(item, 'description', None)
            translated_desc = translation_map.get(desc_path, original_desc)

            food_item_translations.append(
                FoodItemTranslation(
                    food_item_id=item.id,
                    name=translated_name,
                    description=translated_desc
                )
            )
            food_item_index += 1

        return MealTranslation(
            meal_id=meal_id,
            language=language,
            dish_name=translated_dish_name,
            food_items=food_item_translations,
            translated_at=datetime.utcnow()
        )
