"""
Translation service for Phase 3 meal suggestion translation.
Recursively traverses schemas, extracts translatable strings, and translates them using Gemini.
"""
import asyncio
import json
import logging
import time
from dataclasses import asdict, fields
from enum import Enum
from typing import Any, Dict, List, Tuple

from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.prompts.prompt_constants import LANGUAGE_NAMES

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translates meal suggestions by recursively extracting translatable strings
    and batch translating them using Gemini API.
    """

    def __init__(self, generation_service: MealGenerationServicePort):
        """
        Initialize translation service.

        Args:
            generation_service: Service for calling Gemini API
        """
        self._generation_service = generation_service

    async def translate_meal_suggestion(
        self, suggestion: MealSuggestion, target_language: str
    ) -> MealSuggestion:
        """
        Translate a meal suggestion to target language.

        Args:
            suggestion: The meal suggestion to translate
            target_language: ISO 639-1 language code (e.g., 'vi', 'es')

        Returns:
            New MealSuggestion with translated content
        """
        if target_language == "en":
            return suggestion  # No translation needed

        # Extract all translatable strings with their paths
        translatable_items = self._extract_translatable_strings(suggestion)

        if not translatable_items:
            logger.warning(
                f"No translatable strings found for suggestion {suggestion.id}"
            )
            return suggestion

        # Extract just the strings for translation
        strings_to_translate = [item[1] for item in translatable_items]
        paths = [item[0] for item in translatable_items]

        logger.debug(
            f"Translating {len(strings_to_translate)} strings for suggestion {suggestion.id}"
        )

        # Batch translate all strings
        translated_strings = await self._batch_translate(
            strings_to_translate, target_language
        )

        # Create mapping from path to translated string
        translation_map = dict(zip(paths, translated_strings))

        # Reconstruct suggestion with translations
        translated_suggestion = self._reconstruct_with_translations(
            suggestion, translation_map
        )

        return translated_suggestion

    async def translate_meal_suggestions_batch(
        self, suggestions: List[MealSuggestion], target_language: str
    ) -> List[MealSuggestion]:
        """
        Translate multiple meal suggestions in a single API call (optimized).
        
        Extracts all translatable strings from all meals, deduplicates them,
        translates in one batch, then reconstructs each meal.

        Args:
            suggestions: List of meal suggestions to translate
            target_language: ISO 639-1 language code (e.g., 'vi', 'es')

        Returns:
            List of translated MealSuggestion objects in same order
        """
        if target_language == "en":
            return suggestions  # No translation needed

        if not suggestions:
            return []

        logger.info(
            f"Batch translating {len(suggestions)} meals to {target_language}"
        )

        # Extract all strings with (meal_index, path, value) tuples
        all_items = []
        for i, suggestion in enumerate(suggestions):
            items = self._extract_translatable_strings(suggestion)
            for path, value in items:
                all_items.append((i, path, value))

        if not all_items:
            logger.warning("No translatable strings found in any suggestion")
            return suggestions

        # Deduplicate strings while preserving mapping
        # Use dict to maintain order and deduplicate
        unique_strings_dict = {}
        for _, _, value in all_items:
            if value not in unique_strings_dict:
                unique_strings_dict[value] = True

        unique_strings = list(unique_strings_dict.keys())

        logger.info(
            f"Extracted {len(all_items)} total strings, {len(unique_strings)} unique"
        )

        # Split into short and long strings for better token management
        # Long strings (>150 chars) are typically recipe instructions
        # Also filter out very short strings (likely units/abbrevs that don't need translation)
        short_strings = []
        long_strings = []
        skip_strings = []
        
        for s in unique_strings:
            # Skip very short strings (units like "g", "ml", "tsp", "oz")
            if len(s) <= 3 and s.lower() in {"g", "ml", "kg", "l", "oz", "lb", "cup", "tsp", "tbsp"}:
                skip_strings.append(s)
            elif len(s) <= 150:
                short_strings.append(s)
            else:
                long_strings.append(s)

        logger.info(
            f"Split: {len(short_strings)} short, {len(long_strings)} long, {len(skip_strings)} skipped"
        )

        # Translate short and long strings in PARALLEL (not sequential)
        translation_tasks = []
        
        # Add short strings batch task
        if short_strings:
            translation_tasks.append(
                self._batch_translate(short_strings, target_language)
            )
        
        # Add long strings batch tasks (5 at a time, but all in parallel)
        long_string_batches = []
        if long_strings:
            batch_size = 5
            for i in range(0, len(long_strings), batch_size):
                batch = long_strings[i : i + batch_size]
                long_string_batches.append(batch)
                translation_tasks.append(
                    self._batch_translate(batch, target_language)
                )
            logger.info(
                f"Translating in parallel: 1 short batch + {len(long_string_batches)} long batches"
            )
        
        # Execute all translation tasks in parallel with timeout
        translation_start = time.time()
        try:
            # 15 second timeout for all parallel translations
            translated_results = await asyncio.wait_for(
                asyncio.gather(*translation_tasks, return_exceptions=True),
                timeout=15.0
            )
            translation_elapsed = time.time() - translation_start
            
            logger.info(
                f"Parallel translation completed in {translation_elapsed:.2f}s "
                f"({len(translation_tasks)} concurrent API calls)"
            )
        except asyncio.TimeoutError:
            translation_elapsed = time.time() - translation_start
            logger.error(
                f"Translation timeout after {translation_elapsed:.2f}s! "
                f"Returning original suggestions without translation."
            )
            return suggestions  # Return originals on timeout
        
        # Unpack results
        translated_short = []
        translated_long = []
        
        result_idx = 0
        if short_strings:
            result = translated_results[result_idx]
            if isinstance(result, Exception):
                logger.error(f"Short strings translation failed: {result}")
                translated_short = short_strings  # Fallback
            else:
                translated_short = result
            result_idx += 1
        
        if long_strings:
            for batch_result in translated_results[result_idx:]:
                if isinstance(batch_result, Exception):
                    logger.error(f"Long strings batch translation failed: {batch_result}")
                    # Skip this batch, will be handled by fallback
                    continue
                translated_long.extend(batch_result)

        # Combine translations maintaining original order
        translation_map = {}
        for orig, trans in zip(short_strings, translated_short):
            translation_map[orig] = trans
        for orig, trans in zip(long_strings, translated_long):
            translation_map[orig] = trans
        # Skipped strings map to themselves (no translation)
        for orig in skip_strings:
            translation_map[orig] = orig

        # Reconstruct each suggestion with its translations
        translated_suggestions = []
        for i, suggestion in enumerate(suggestions):
            # Build translation map for this specific meal
            meal_translations = {
                path: translation_map[value]
                for meal_idx, path, value in all_items
                if meal_idx == i
            }

            # Reconstruct with translations
            translated = self._reconstruct_with_translations(
                suggestion, meal_translations
            )
            translated_suggestions.append(translated)

        logger.info(
            f"Batch translation complete: translated {len(unique_strings)} unique strings "
            f"for {len(suggestions)} meals"
        )

        return translated_suggestions

    def _extract_translatable_strings(
        self, obj: Any, path: str = ""
    ) -> List[Tuple[str, str]]:
        """
        Recursively extract translatable strings with their paths.

        Args:
            obj: Object to traverse (dataclass, dict, list, etc.)
            path: Current path in the object hierarchy

        Returns:
            List of (path, string) tuples for translatable content
        """
        translatable = []

        if isinstance(obj, str):
            # Only translate non-empty strings that are not IDs
            if obj and not self._is_id_path(path):
                translatable.append((path, obj))

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                item_path = f"{path}[{i}]" if path else f"[{i}]"
                translatable.extend(
                    self._extract_translatable_strings(item, item_path)
                )

        elif hasattr(obj, "__dict__"):  # Dataclass or object
            for key, value in obj.__dict__.items():
                # Skip IDs, enums, numbers, booleans, None
                if self._should_skip_field(key, value):
                    continue

                field_path = f"{path}.{key}" if path else key
                translatable.extend(
                    self._extract_translatable_strings(value, field_path)
                )

        elif isinstance(obj, dict):
            for key, value in obj.items():
                if self._should_skip_field(key, value):
                    continue

                field_path = f"{path}.{key}" if path else key
                translatable.extend(
                    self._extract_translatable_strings(value, field_path)
                )

        return translatable

    def _should_skip_field(self, key: str, value: Any) -> bool:
        """
        Determine if a field should be skipped during translation.

        Args:
            key: Field name
            value: Field value

        Returns:
            True if field should be skipped
        """
        # Skip IDs
        if key.endswith("_id") or key == "id":
            return True

        # Skip non-string types
        if isinstance(value, (int, float, bool, type(None))):
            return True

        # Skip enum types
        if isinstance(value, Enum):
            return True

        # Skip datetime objects
        if hasattr(value, "isoformat"):  # datetime-like
            return True

        return False

    def _is_id_path(self, path: str) -> bool:
        """
        Check if a path represents an ID field.

        Args:
            path: Field path (e.g., "meal_name", "ingredients[0].name")

        Returns:
            True if path represents an ID
        """
        return path.endswith("_id") or path.endswith(".id") or path == "id"

    async def _batch_translate(
        self, strings: List[str], target_language: str
    ) -> List[str]:
        """
        Translate strings using Gemini API with dynamic token sizing.

        Args:
            strings: List of strings to translate
            target_language: Target language code

        Returns:
            List of translated strings in same order
        """
        if not strings:
            return []

        lang_name = LANGUAGE_NAMES.get(target_language, "English")

        # Dynamic token limit calculation
        # Estimate: ~2 tokens per word for input, ~2x for translation output
        estimated_input_tokens = sum(len(s.split()) * 2 for s in strings)
        token_limit = max(4000, int(estimated_input_tokens * 2.5))
        token_limit = min(token_limit, 8000)  # Cap at 8000 to avoid timeouts

        logger.info(
            f"Translating {len(strings)} strings to {lang_name} | "
            f"estimated_tokens={estimated_input_tokens} | token_limit={token_limit}"
        )

        prompt = f"""Translate ALL {len(strings)} text strings below to {lang_name}.

CRITICAL RULES:
1. Translate EVERY single string - do NOT skip any
2. Translate ALL food terms: "salt" → "muối", "black pepper" → "tiêu đen", "chicken breast" → "ức gà"
3. Translate ALL cooking instructions to natural {lang_name}
4. Keep measurement units UNCHANGED: g, ml, tbsp, tsp, cup, oz, minutes
5. Keep numbers EXACTLY as-is
6. Return EXACTLY {len(strings)} translations in SAME ORDER as input

Input strings ({len(strings)} total):
{json.dumps(strings, ensure_ascii=False, indent=2)}

Output: Return ONLY a JSON object with a "translations" array containing EXACTLY {len(strings)} translated strings."""

        system_message = (
            f"You are a professional {lang_name} translator specializing in recipe and food content. "
            f"Your task is to translate ALL content to natural, fluent {lang_name}. "
            f"CRITICAL: You MUST translate all {len(strings)} strings completely. "
            f"Return ONLY valid JSON with all {len(strings)} translations."
        )

        try:
            result = await asyncio.to_thread(
                self._generation_service.generate_meal_plan,
                prompt,
                system_message,
                "json",
                token_limit,  # Dynamic token limit
            )

            # Extract translations from response
            translations = result.get("translations", [])

            # Validate translation count
            if len(translations) != len(strings):
                logger.error(
                    f"Translation count mismatch: expected {len(strings)}, got {len(translations)}. "
                    f"First 3 input: {strings[:3]} | First 3 output: {translations[:3]}"
                )
                # Pad with original strings if needed
                while len(translations) < len(strings):
                    missing_idx = len(translations)
                    logger.warning(
                        f"Missing translation at index {missing_idx}: {strings[missing_idx][:50]}..."
                    )
                    translations.append(strings[missing_idx])

            # Validate each translation is non-empty
            for i in range(len(strings)):
                if not translations[i] or not translations[i].strip():
                    logger.warning(
                        f"Empty translation at index {i}, using original: {strings[i][:50]}..."
                    )
                    translations[i] = strings[i]

            # Log sample translations for debugging
            if translations:
                logger.debug(
                    f"Sample translations: '{strings[0][:30]}' → '{translations[0][:30]}'"
                )

            return translations[: len(strings)]  # Ensure exact count

        except Exception as e:
            logger.error(
                f"Translation failed: {type(e).__name__}: {str(e)[:200]}. "
                f"Returning original strings as fallback."
            )
            return strings  # Fallback to original

    def _reconstruct_with_translations(
        self, obj: Any, translation_map: Dict[str, str]
    ) -> Any:
        """
        Reconstruct object with translated strings.

        Args:
            obj: Original object to reconstruct
            translation_map: Mapping from path to translated string

        Returns:
            New object with translated content
        """
        # Convert dataclass to dict for easier manipulation
        if hasattr(obj, "__dataclass_fields__"):
            obj_dict = asdict(obj)
        elif isinstance(obj, dict):
            obj_dict = obj.copy()
        else:
            return obj

        # Apply translations by setting values using paths
        for path, translated_value in translation_map.items():
            self._set_nested_value(obj_dict, path, translated_value)

        # Reconstruct dataclass from dict
        if hasattr(obj, "__dataclass_fields__"):
            return self._dict_to_dataclass(obj_dict, type(obj))
        else:
            return obj_dict

    def _set_nested_value(self, obj_dict: dict, path: str, value: Any) -> None:
        """
        Set a value in a nested dict using a path string.

        Args:
            obj_dict: Dictionary to modify
            path: Path like "meal_name" or "ingredients[0].name"
            value: Value to set
        """
        parts = self._parse_path(path)
        if not parts:
            return

        # Navigate to the parent container
        current = obj_dict
        for part in parts[:-1]:
            if isinstance(part, int):
                # List index
                if isinstance(current, list) and 0 <= part < len(current):
                    current = current[part]
                else:
                    return  # Invalid path
            else:
                # Dict key
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return  # Invalid path

        # Set the final value
        last_part = parts[-1]
        if isinstance(last_part, int):
            if isinstance(current, list) and 0 <= last_part < len(current):
                current[last_part] = value
        else:
            if isinstance(current, dict) and last_part in current:
                current[last_part] = value

    def _parse_path(self, path: str) -> List[Any]:
        """
        Parse a path string into a list of keys/indices.

        Args:
            path: Path like "meal_name" or "ingredients[0].name"

        Returns:
            List of keys (str) and indices (int)
        """
        parts = []
        current_key = ""
        i = 0

        while i < len(path):
            if path[i] == "[":
                if current_key:
                    parts.append(current_key)
                    current_key = ""
                # Find closing bracket
                j = i + 1
                while j < len(path) and path[j] != "]":
                    j += 1
                if j < len(path):
                    index_str = path[i + 1 : j]
                    try:
                        parts.append(int(index_str))
                    except ValueError:
                        return []  # Invalid index
                    i = j + 1
            elif path[i] == ".":
                if current_key:
                    parts.append(current_key)
                    current_key = ""
                i += 1
            else:
                current_key += path[i]
                i += 1

        if current_key:
            parts.append(current_key)

        return parts

    def _dict_to_dataclass(self, obj_dict: dict, dataclass_type: type) -> Any:
        """
        Convert a dict back to a dataclass instance, handling nested structures.

        Args:
            obj_dict: Dictionary representation
            dataclass_type: The dataclass type to instantiate

        Returns:
            Instance of dataclass_type
        """
        if not hasattr(dataclass_type, "__dataclass_fields__"):
            return obj_dict

        field_values = {}
        for field in fields(dataclass_type):
            field_name = field.name
            if field_name not in obj_dict:
                continue

            value = obj_dict[field_name]

            # Handle nested dataclasses
            if hasattr(field.type, "__dataclass_fields__"):
                field_values[field_name] = self._dict_to_dataclass(
                    value, field.type
                )
            # Handle lists of dataclasses
            elif (
                hasattr(field.type, "__origin__")
                and field.type.__origin__ is list
                and hasattr(field.type.__args__[0], "__dataclass_fields__")
            ):
                item_type = field.type.__args__[0]
                field_values[field_name] = [
                    self._dict_to_dataclass(item, item_type) for item in value
                ]
            else:
                field_values[field_name] = value

        return dataclass_type(**field_values)
"""
Translation service for meal content translation.
Recursively traverses schemas, extracts translatable strings, and translates them using Gemini.

NOTE: This service implements the post-generation translation approach (PR #61).
Content is generated in English, then translated to target language.
"""
import asyncio
import functools
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Tuple, Union

from src.domain.ports.meal_generation_service_port import MealGenerationServicePort
from src.domain.services.prompts.prompt_constants import LANGUAGE_NAMES

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translates meal content by recursively extracting translatable strings
    and batch translating them using Gemini API.

    Supports:
    - MealSuggestion (meal suggestions)
    - Dict[str, Any] (meal analysis results)
    """

    def __init__(self, generation_service: MealGenerationServicePort):
        """
        Initialize translation service.

        Args:
            generation_service: Service for calling Gemini API
        """
        self._generation_service = generation_service

    async def translate_meal_analysis(
        self, analysis_result: Dict[str, Any], target_language: str
    ) -> Dict[str, Any]:
        """
        Translate meal analysis result to target language.

        Args:
            analysis_result: The meal analysis dictionary from VisionAIService
            target_language: ISO 639-1 language code (e.g., 'vi', 'es')

        Returns:
            New dictionary with translated content
        """
        if target_language == "en":
            return analysis_result  # No translation needed

        # Extract structured_data which contains the actual content
        structured_data = analysis_result.get("structured_data", {})
        if not structured_data:
            logger.warning("No structured_data in analysis result")
            return analysis_result

        # Extract translatable strings from structured_data
        translatable_items = self._extract_translatable_strings(structured_data)

        if not translatable_items:
            logger.warning("No translatable strings found in meal analysis")
            return analysis_result

        # Extract strings for translation
        strings_to_translate = [item[1] for item in translatable_items]
        paths = [item[0] for item in translatable_items]

        logger.info(
            f"Translating {len(strings_to_translate)} strings from meal analysis "
            f"to {target_language}"
        )

        # Batch translate
        translated_strings = await self._batch_translate(
            strings_to_translate, target_language
        )

        # Create mapping from path to translated string
        translation_map = dict(zip(paths, translated_strings))

        # Reconstruct structured_data with translations
        translated_data = self._reconstruct_dict_with_translations(
            structured_data, translation_map
        )

        # Return full result with translated structured_data
        return {
            **analysis_result,
            "structured_data": translated_data,
            "translated_to": target_language,
        }

    def _extract_translatable_strings(
        self, obj: Any, path: str = ""
    ) -> List[Tuple[str, str]]:
        """
        Recursively extract translatable strings with their paths.

        Args:
            obj: Object to traverse (dataclass, dict, list, etc.)
            path: Current path in the object hierarchy

        Returns:
            List of (path, string) tuples for translatable content
        """
        translatable = []

        if isinstance(obj, str):
            # Only translate non-empty strings that are not IDs
            if obj and not self._is_id_path(path):
                translatable.append((path, obj))

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                item_path = f"{path}[{i}]" if path else f"[{i}]"
                translatable.extend(
                    self._extract_translatable_strings(item, item_path)
                )

        elif hasattr(obj, "__dict__"):  # Dataclass or object
            for key, value in obj.__dict__.items():
                if self._should_skip_field(key, value):
                    continue
                field_path = f"{path}.{key}" if path else key
                translatable.extend(
                    self._extract_translatable_strings(value, field_path)
                )

        elif isinstance(obj, dict):
            for key, value in obj.items():
                if self._should_skip_field(key, value):
                    continue
                field_path = f"{path}.{key}" if path else key
                translatable.extend(
                    self._extract_translatable_strings(value, field_path)
                )

        return translatable

    def _should_skip_field(self, key: str, value: Any) -> bool:
        """
        Determine if a field should be skipped during translation.

        Args:
            key: Field name
            value: Field value

        Returns:
            True if field should be skipped
        """
        # Skip IDs
        if key.endswith("_id") or key == "id":
            return True

        # Skip non-string types
        if isinstance(value, (int, float, bool, type(None))):
            return True

        # Skip enum types
        if isinstance(value, Enum):
            return True

        # Skip datetime objects
        if hasattr(value, "isoformat"):
            return True

        # Skip unit fields (measurement units should stay in English)
        if key == "unit":
            return True

        return False

    def _is_id_path(self, path: str) -> bool:
        """Check if a path represents an ID field."""
        return path.endswith("_id") or path.endswith(".id") or path == "id"

    async def _batch_translate(
        self, strings: List[str], target_language: str
    ) -> List[str]:
        """
        Translate strings using Gemini API with dynamic token sizing.

        Args:
            strings: List of strings to translate
            target_language: Target language code

        Returns:
            List of translated strings in same order
        """
        if not strings:
            return []

        lang_name = LANGUAGE_NAMES.get(target_language, "English")

        # Dynamic token limit calculation
        estimated_input_tokens = sum(len(s.split()) * 2 for s in strings)
        token_limit = max(4000, int(estimated_input_tokens * 2.5))
        token_limit = min(token_limit, 8000)

        logger.info(
            f"Translating {len(strings)} strings to {lang_name} | "
            f"estimated_tokens={estimated_input_tokens} | token_limit={token_limit}"
        )

        prompt = f"""Translate ALL {len(strings)} text strings below to {lang_name}.

CRITICAL RULES:
1. Translate EVERY single string - do NOT skip any
2. Translate ALL food terms: "salt" → "muối", "black pepper" → "tiêu đen", "chicken breast" → "ức gà"
3. Translate ALL cooking instructions to natural {lang_name}
4. Keep measurement units UNCHANGED: g, ml, tbsp, tsp, cup, oz, minutes
5. Keep numbers EXACTLY as-is
6. Return EXACTLY {len(strings)} translations in SAME ORDER as input

Input strings ({len(strings)} total):
{json.dumps(strings, ensure_ascii=False, indent=2)}

Output: Return ONLY a JSON object with a "translations" array containing EXACTLY {len(strings)} translated strings."""

        system_message = (
            f"You are a professional {lang_name} translator specializing in recipe and food content. "
            f"Your task is to translate ALL content to natural, fluent {lang_name}. "
            f"CRITICAL: You MUST translate all {len(strings)} strings completely. "
            f"Return ONLY valid JSON with all {len(strings)} translations."
        )

        try:
            generate_func = functools.partial(
                self._generation_service.generate_meal_plan,
                prompt,
                system_message,
                "json",
                token_limit,
            )
            result = await asyncio.to_thread(generate_func)

            translations = result.get("translations", [])

            # Validate translation count
            if len(translations) != len(strings):
                logger.error(
                    f"Translation count mismatch: expected {len(strings)}, got {len(translations)}"
                )
                while len(translations) < len(strings):
                    missing_idx = len(translations)
                    translations.append(strings[missing_idx])

            # Validate each translation is non-empty
            for i in range(len(strings)):
                if i < len(translations) and (not translations[i] or not translations[i].strip()):
                    translations[i] = strings[i]

            return translations[: len(strings)]

        except Exception as e:
            logger.error(
                f"Translation failed: {type(e).__name__}: {str(e)[:200]}. "
                f"Returning original strings as fallback."
            )
            return strings

    def _reconstruct_dict_with_translations(
        self, obj_dict: Dict[str, Any], translation_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Reconstruct dictionary with translated strings.

        Args:
            obj_dict: Original dictionary
            translation_map: Mapping from path to translated string

        Returns:
            New dictionary with translated content
        """
        result = obj_dict.copy()

        for path, translated_value in translation_map.items():
            self._set_nested_value(result, path, translated_value)

        return result

    def _set_nested_value(self, obj_dict: dict, path: str, value: Any) -> None:
        """
        Set a value in a nested dict using a path string.

        Args:
            obj_dict: Dictionary to modify
            path: Path like "dish_name" or "foods[0].name"
            value: Value to set
        """
        parts = self._parse_path(path)
        if not parts:
            return

        current = obj_dict
        for part in parts[:-1]:
            if isinstance(part, int):
                if isinstance(current, list) and 0 <= part < len(current):
                    current = current[part]
                else:
                    return
            else:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return

        last_part = parts[-1]
        if isinstance(last_part, int):
            if isinstance(current, list) and 0 <= last_part < len(current):
                current[last_part] = value
        else:
            if isinstance(current, dict) and last_part in current:
                current[last_part] = value

    def _parse_path(self, path: str) -> List[Union[str, int]]:
        """
        Parse a path string into a list of keys/indices.

        Args:
            path: Path like "dish_name" or "foods[0].name"

        Returns:
            List of keys (str) and indices (int)
        """
        parts = []
        current_key = ""
        i = 0

        while i < len(path):
            if path[i] == "[":
                if current_key:
                    parts.append(current_key)
                    current_key = ""
                j = i + 1
                while j < len(path) and path[j] != "]":
                    j += 1
                if j < len(path):
                    index_str = path[i + 1 : j]
                    try:
                        parts.append(int(index_str))
                    except ValueError:
                        return []
                    i = j + 1
            elif path[i] == ".":
                if current_key:
                    parts.append(current_key)
                    current_key = ""
                i += 1
            else:
                current_key += path[i]
                i += 1

        if current_key:
            parts.append(current_key)

        return parts
