"""
Batch translation of meal suggestions via Gemini API.
String extraction/reconstruction helpers: translation_string_utils.py
"""
import asyncio
import json
import logging
import time
from typing import List

from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.prompts.prompt_constants import LANGUAGE_NAMES
from src.domain.services.meal_suggestion.translation_string_utils import (
    extract_translatable_strings,
    reconstruct_with_translations,
)

logger = logging.getLogger(__name__)

# Measurement units that never need translation
_SKIP_UNITS = {"g", "ml", "kg", "l", "oz", "lb", "cup", "tsp", "tbsp"}


class TranslationService:
    """
    Translates meal suggestions by batch-translating all translatable strings
    via a single Gemini API call per batch.
    """

    def __init__(self, generation_service: MealGenerationServicePort) -> None:
        self._generation_service = generation_service

    async def translate_meal_suggestion(
        self, suggestion: MealSuggestion, target_language: str
    ) -> MealSuggestion:
        """Translate a single meal suggestion to target_language."""
        if target_language == "en":
            return suggestion

        items = extract_translatable_strings(suggestion)
        if not items:
            logger.warning(f"No translatable strings for suggestion {suggestion.id}")
            return suggestion

        paths = [p for p, _ in items]
        strings = [s for _, s in items]
        translated = await self._batch_translate(strings, target_language)
        translation_map = dict(zip(paths, translated))
        return reconstruct_with_translations(suggestion, translation_map)

    async def translate_meal_suggestions_batch(
        self, suggestions: List[MealSuggestion], target_language: str
    ) -> List[MealSuggestion]:
        """Translate multiple suggestions in parallel: deduplicates, batches short/long, then reconstructs."""
        if target_language == "en":
            return suggestions
        if not suggestions:
            return []

        logger.info(f"Batch translating {len(suggestions)} meals to {target_language}")

        all_items = [
            (i, path, value)
            for i, suggestion in enumerate(suggestions)
            for path, value in extract_translatable_strings(suggestion)
        ]
        if not all_items:
            logger.warning("No translatable strings found in any suggestion")
            return suggestions

        unique_strings = list(dict.fromkeys(v for _, _, v in all_items))
        short_strings, long_strings, skip_strings = [], [], []
        for s in unique_strings:
            if len(s) <= 3 and s.lower() in _SKIP_UNITS:
                skip_strings.append(s)
            elif len(s) <= 150:
                short_strings.append(s)
            else:
                long_strings.append(s)
        logger.info(f"{len(unique_strings)} unique strings: {len(short_strings)} short, {len(long_strings)} long, {len(skip_strings)} skipped")

        # Build parallel tasks: 1 short batch + N long batches of 5
        translation_tasks = []
        if short_strings:
            translation_tasks.append(self._batch_translate(short_strings, target_language))
        long_batches = [long_strings[i: i + 5] for i in range(0, len(long_strings), 5)]
        for batch in long_batches:
            translation_tasks.append(self._batch_translate(batch, target_language))
        if long_batches:
            logger.info(f"Parallel: 1 short + {len(long_batches)} long batches")

        t0 = time.time()
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*translation_tasks, return_exceptions=True), timeout=15.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Translation timeout after {time.time()-t0:.2f}s — returning originals.")
            return suggestions
        logger.info(f"Parallel translation done in {time.time()-t0:.2f}s ({len(translation_tasks)} calls)")

        # Unpack results into short / long lists
        translated_short: List[str] = []
        translated_long: List[str] = []
        result_idx = 0
        if short_strings:
            r = results[result_idx]
            if isinstance(r, Exception):
                logger.error(f"Short batch failed: {r}")
                translated_short = short_strings
            else:
                translated_short = r
            result_idx += 1
        for r in results[result_idx:]:
            if isinstance(r, Exception):
                logger.error(f"Long batch failed: {r}")
            else:
                translated_long.extend(r)

        # Build unified translation map
        translation_map = {}
        for orig, trans in zip(short_strings, translated_short):
            translation_map[orig] = trans
        for orig, trans in zip(long_strings, translated_long):
            translation_map[orig] = trans
        for orig in skip_strings:
            translation_map[orig] = orig

        # Reconstruct each suggestion
        translated_suggestions = []
        for i, suggestion in enumerate(suggestions):
            meal_map = {
                path: translation_map[value]
                for meal_idx, path, value in all_items
                if meal_idx == i and value in translation_map
            }
            translated_suggestions.append(
                reconstruct_with_translations(suggestion, meal_map)
            )

        logger.info(
            f"Batch translation complete: {len(unique_strings)} unique strings "
            f"for {len(suggestions)} meals"
        )
        return translated_suggestions

    async def _batch_translate(
        self, strings: List[str], target_language: str
    ) -> List[str]:
        """Call Gemini to translate a list of strings. Returns originals on failure."""
        if not strings:
            return []

        lang_name = LANGUAGE_NAMES.get(target_language, "English")
        estimated_input_tokens = sum(len(s.split()) * 2 for s in strings)
        token_limit = min(max(4000, int(estimated_input_tokens * 2.5)), 8000)

        logger.info(
            f"Translating {len(strings)} strings to {lang_name} | "
            f"estimated_tokens={estimated_input_tokens} | token_limit={token_limit}"
        )

        n = len(strings)
        prompt = (
            f"Translate ALL {n} strings below to {lang_name}. RULES: translate every string, "
            f"keep units (g,ml,tbsp,tsp,cup,oz,min) unchanged, keep numbers as-is, "
            f"return EXACTLY {n} translations in same order.\n"
            f"Input:\n{json.dumps(strings, ensure_ascii=False, indent=2)}\n"
            f'Output: ONLY a JSON object {{"translations":[...{n} items...]}}'
        )
        system_message = (
            f"Professional {lang_name} food/recipe translator. "
            f"Return ONLY valid JSON with all {n} translations."
        )

        try:
            result = await asyncio.to_thread(
                self._generation_service.generate_meal_plan, prompt, system_message, "json", token_limit,
            )
            translations: List[str] = result.get("translations", [])
            # Pad missing entries with originals
            while len(translations) < len(strings):
                idx = len(translations)
                logger.warning(f"Missing translation at {idx}: {strings[idx][:50]}...")
                translations.append(strings[idx])
            # Replace empty entries with originals
            for i in range(len(strings)):
                if not (translations[i] or "").strip():
                    logger.warning(f"Empty translation at {i}, using original: {strings[i][:50]}...")
                    translations[i] = strings[i]
            if translations:
                logger.debug(f"Sample: '{strings[0][:30]}' → '{translations[0][:30]}'")
            return translations[: len(strings)]

        except Exception as e:
            logger.error(f"Translation failed: {type(e).__name__}: {str(e)[:200]}. Returning originals.")
            return strings
