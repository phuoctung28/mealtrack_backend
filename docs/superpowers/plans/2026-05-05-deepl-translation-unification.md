# DeepL Translation Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify translation across 4 AI flows (ingredient recognition, food search, barcode lookup, parse meal text) to use DeepL instead of Gemini or no translation.

**Architecture:** Create a core `DeepLTextTranslationService` for text translation. Refactor existing `DeepLMealTranslationService` and `DeepLSuggestionTranslationService` to use the core service internally (layered approach). Inject the core service into 4 handlers, replacing Gemini-based or missing translation.

**Tech Stack:** Python 3.11+, DeepL API, FastAPI dependency injection, pytest

---

## File Structure

**New files:**
- `src/domain/services/translation/__init__.py` — package init
- `src/domain/services/translation/deepl_text_translation_service.py` — unified text translation service
- `tests/unit/domain/services/translation/__init__.py` — test package init
- `tests/unit/domain/services/translation/test_deepl_text_translation_service.py` — unit tests

**Modified files:**
- `src/domain/ports/deepl_translation_port.py` — add `translate_to_english()` method
- `src/infra/adapters/deepl_translation_adapter.py` — implement `translate_to_english()`
- `src/api/base_dependencies.py` — add `get_deepl_text_translation_service()` singleton, update other singletons
- `src/api/dependencies/event_bus.py` — wire new service to handlers
- `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py` — add translation
- `src/app/handlers/query_handlers/search_foods_query_handler.py` — swap translation service
- `src/app/handlers/query_handlers/lookup_barcode_query_handler.py` — swap translation service
- `src/app/handlers/command_handlers/parse_meal_text_handler.py` — replace Gemini translation
- `src/domain/services/meal_analysis/deepl_meal_translation_service.py` — use core service internally
- `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py` — use core service internally

**Deleted files:**
- `src/domain/services/food_search_translation_service.py` — replaced by DeepL service

---

### Task 1: Enhance DeepL Port with Reverse Translation

**Files:**
- Modify: `src/domain/ports/deepl_translation_port.py`
- Test: `tests/unit/infra/adapters/test_deepl_translation_adapter.py` (if exists, otherwise skip)

- [ ] **Step 1: Add abstract method to port**

Edit `src/domain/ports/deepl_translation_port.py` to add the new method:

```python
@abstractmethod
async def translate_to_english(self, texts: List[str], source_lang: str) -> List[str]:
    """
    Translate a list of strings from source language to English.

    Args:
        texts: Strings in source language to translate.
        source_lang: ISO 639-1 source code (e.g. 'vi', 'fr'). If unknown,
            implementation may use auto-detect.

    Returns:
        Translated English strings in the same order as input.

    Raises:
        Exception: On any API-level failure.
    """
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "from src.domain.ports.deepl_translation_port import DeepLTranslationPort"`
Expected: No import errors

- [ ] **Step 3: Commit**

```bash
git add src/domain/ports/deepl_translation_port.py
git commit -m "feat(port): add translate_to_english to DeepLTranslationPort"
```

---

### Task 2: Implement Reverse Translation in Adapter

**Files:**
- Modify: `src/infra/adapters/deepl_translation_adapter.py`

- [ ] **Step 1: Add source language mapping constant**

After the existing `_LANG_MAP`, add a reverse mapping for source languages:

```python
# Map from ISO 639-1 to DeepL source-language codes.
# DeepL source codes don't distinguish regional variants.
_SOURCE_LANG_MAP: dict = {
    "en": "EN",
    "vi": "VI",
    "es": "ES",
    "fr": "FR",
    "de": "DE",
    "ja": "JA",
    "zh": "ZH",
    "ko": "KO",
    "pt": "PT",
    "ru": "RU",
    "it": "IT",
    "nl": "NL",
    "pl": "PL",
    "tr": "TR",
    "uk": "UK",
    "id": "ID",
}
```

- [ ] **Step 2: Implement translate_to_english method**

Add this method to `DeepLTranslationAdapter` class:

```python
async def translate_to_english(self, texts: List[str], source_lang: str) -> List[str]:
    """
    Translate a batch of strings to English with a single DeepL API call.

    Uses explicit source language if mapped, otherwise auto-detect.
    """
    if not texts:
        return []

    # English → English: no DeepL call needed
    if source_lang.lower() == "en":
        return list(texts)

    # Map source language; use None for auto-detect if unknown
    deepl_source = _SOURCE_LANG_MAP.get(source_lang.lower())

    try:
        results = await asyncio.to_thread(
            self._translator.translate_text,
            texts,
            target_lang="EN-US",
            source_lang=deepl_source,  # None triggers auto-detect
        )
        if isinstance(results, list):
            return [r.text for r in results]
        return [results.text]
    except deepl.DeepLException as exc:
        logger.error("DeepL API error (to EN from %s): %s", source_lang, exc)
        raise
```

- [ ] **Step 3: Verify syntax**

Run: `python -c "from src.infra.adapters.deepl_translation_adapter import DeepLTranslationAdapter"`
Expected: No import errors

- [ ] **Step 4: Commit**

```bash
git add src/infra/adapters/deepl_translation_adapter.py
git commit -m "feat(adapter): implement translate_to_english in DeepLTranslationAdapter"
```

---

### Task 3: Create DeepLTextTranslationService with Tests (TDD)

**Files:**
- Create: `src/domain/services/translation/__init__.py`
- Create: `src/domain/services/translation/deepl_text_translation_service.py`
- Create: `tests/unit/domain/services/translation/__init__.py`
- Create: `tests/unit/domain/services/translation/test_deepl_text_translation_service.py`

- [ ] **Step 1: Create package init files**

Create `src/domain/services/translation/__init__.py`:
```python
"""Translation services package."""
from .deepl_text_translation_service import DeepLTextTranslationService

__all__ = ["DeepLTextTranslationService"]
```

Create `tests/unit/domain/services/translation/__init__.py`:
```python
"""Translation service tests."""
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit/domain/services/translation/test_deepl_text_translation_service.py`:

```python
"""Unit tests for DeepLTextTranslationService."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)


@pytest.fixture
def mock_deepl_port():
    """Create a mock DeepL port."""
    port = MagicMock()
    port.translate_texts = AsyncMock(return_value=["Xin chào", "Tạm biệt"])
    port.translate_to_english = AsyncMock(return_value=["Hello", "Goodbye"])
    return port


@pytest.fixture
def service(mock_deepl_port):
    """Create service with mocked port."""
    return DeepLTextTranslationService(deepl_port=mock_deepl_port)


class TestTranslateTexts:
    """Tests for translate_texts method."""

    @pytest.mark.asyncio
    async def test_translates_texts_to_target_language(self, service, mock_deepl_port):
        result = await service.translate_texts(["Hello", "Goodbye"], "vi")

        mock_deepl_port.translate_texts.assert_called_once_with(["Hello", "Goodbye"], "vi")
        assert result == ["Xin chào", "Tạm biệt"]

    @pytest.mark.asyncio
    async def test_returns_original_for_english_target(self, service, mock_deepl_port):
        result = await service.translate_texts(["Hello"], "en")

        mock_deepl_port.translate_texts.assert_not_called()
        assert result == ["Hello"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_empty_input(self, service, mock_deepl_port):
        result = await service.translate_texts([], "vi")

        mock_deepl_port.translate_texts.assert_not_called()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_original_on_error(self, service, mock_deepl_port):
        mock_deepl_port.translate_texts.side_effect = Exception("API error")

        result = await service.translate_texts(["Hello"], "vi")

        assert result == ["Hello"]


class TestTranslateToEnglish:
    """Tests for translate_to_english method."""

    @pytest.mark.asyncio
    async def test_translates_to_english(self, service, mock_deepl_port):
        result = await service.translate_to_english(["Xin chào"], "vi")

        mock_deepl_port.translate_to_english.assert_called_once_with(["Xin chào"], "vi")
        assert result == ["Hello", "Goodbye"]  # Mock returns both

    @pytest.mark.asyncio
    async def test_returns_original_for_english_source(self, service, mock_deepl_port):
        result = await service.translate_to_english(["Hello"], "en")

        mock_deepl_port.translate_to_english.assert_not_called()
        assert result == ["Hello"]

    @pytest.mark.asyncio
    async def test_returns_original_on_error(self, service, mock_deepl_port):
        mock_deepl_port.translate_to_english.side_effect = Exception("API error")

        result = await service.translate_to_english(["Xin chào"], "vi")

        assert result == ["Xin chào"]


class TestTranslateFoodNames:
    """Tests for translate_food_names method."""

    @pytest.mark.asyncio
    async def test_translates_food_names(self, service, mock_deepl_port):
        mock_deepl_port.translate_texts.return_value = ["Thịt gà", "Cơm"]
        foods = [
            {"name": "Chicken", "calories": 200},
            {"description": "Rice", "protein": 5},
        ]

        result = await service.translate_food_names(foods, "vi")

        assert result[0]["name"] == "Thịt gà"
        assert result[0]["name_original"] == "Chicken"
        assert result[1]["description"] == "Cơm"
        assert result[1]["description_original"] == "Rice"

    @pytest.mark.asyncio
    async def test_skips_translation_for_english(self, service, mock_deepl_port):
        foods = [{"name": "Chicken"}]

        result = await service.translate_food_names(foods, "en")

        mock_deepl_port.translate_texts.assert_not_called()
        assert result == foods

    @pytest.mark.asyncio
    async def test_returns_original_on_error(self, service, mock_deepl_port):
        mock_deepl_port.translate_texts.side_effect = Exception("API error")
        foods = [{"name": "Chicken"}]

        result = await service.translate_food_names(foods, "vi")

        assert result[0]["name"] == "Chicken"
        assert "name_original" not in result[0]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/domain/services/translation/test_deepl_text_translation_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 4: Implement the service**

Create `src/domain/services/translation/deepl_text_translation_service.py`:

```python
"""
DeepL-backed text translation service.

Provides simple text translation for food search, ingredient recognition,
barcode lookup, and meal text parsing flows.
"""
import logging
from typing import Any, Dict, List

from src.domain.ports.deepl_translation_port import DeepLTranslationPort

logger = logging.getLogger(__name__)


class DeepLTextTranslationService:
    """
    Translates text via DeepL for various flows.

    On any error, returns original content and logs a warning.
    Never blocks the main flow due to translation failure.
    """

    def __init__(self, deepl_port: DeepLTranslationPort) -> None:
        self._deepl = deepl_port

    async def translate_texts(
        self, texts: List[str], target_lang: str
    ) -> List[str]:
        """
        Translate texts from English to target language.

        Args:
            texts: English strings to translate.
            target_lang: ISO 639-1 target code (e.g. 'vi', 'fr').

        Returns:
            Translated strings. On error, returns original texts.
        """
        if not texts or target_lang == "en":
            return list(texts) if texts else []

        try:
            return await self._deepl.translate_texts(texts, target_lang)
        except Exception as exc:
            logger.warning("DeepL translate_texts failed (lang=%s): %s", target_lang, exc)
            return list(texts)

    async def translate_to_english(
        self, texts: List[str], source_lang: str
    ) -> List[str]:
        """
        Translate texts from source language to English.

        Used for translating search queries before lookup.

        Args:
            texts: Strings in source language.
            source_lang: ISO 639-1 source code.

        Returns:
            English strings. On error, returns original texts.
        """
        if not texts or source_lang == "en":
            return list(texts) if texts else []

        try:
            return await self._deepl.translate_to_english(texts, source_lang)
        except Exception as exc:
            logger.warning("DeepL translate_to_english failed (lang=%s): %s", source_lang, exc)
            return list(texts)

    async def translate_food_names(
        self, foods: List[Dict[str, Any]], target_lang: str
    ) -> List[Dict[str, Any]]:
        """
        Translate food name/description fields to target language.

        Modifies dicts in-place, preserving originals as name_original/description_original.

        Args:
            foods: List of food dicts with 'name' or 'description' fields.
            target_lang: ISO 639-1 target code.

        Returns:
            Same list with translated fields. On error, returns unchanged.
        """
        if not foods or target_lang == "en":
            return foods

        # Extract unique names to translate
        names: List[str] = []
        for food in foods:
            name = food.get("description") or food.get("name", "")
            if name and name not in names:
                names.append(name)

        if not names:
            return foods

        try:
            translated = await self._deepl.translate_texts(names, target_lang)

            # Pad if DeepL returns fewer items
            while len(translated) < len(names):
                translated.append(names[len(translated)])

            # Build lookup
            name_map = dict(zip(names, translated))

            # Apply translations
            for food in foods:
                original = food.get("description") or food.get("name", "")
                translated_name = name_map.get(original)
                if translated_name:
                    if "description" in food:
                        food["description_original"] = original
                        food["description"] = translated_name
                    if "name" in food:
                        food["name_original"] = original
                        food["name"] = translated_name

            return foods

        except Exception as exc:
            logger.warning("DeepL translate_food_names failed (lang=%s): %s", target_lang, exc)
            return foods
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/domain/services/translation/test_deepl_text_translation_service.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/domain/services/translation/ tests/unit/domain/services/translation/
git commit -m "feat: add DeepLTextTranslationService with tests"
```

---

### Task 4: Add Singleton Dependency

**Files:**
- Modify: `src/api/base_dependencies.py`

- [ ] **Step 1: Add singleton getter**

Add after `get_deepl_meal_translation_service()` (around line 448):

```python
_deepl_text_translation_service = None


def get_deepl_text_translation_service():
    """Get DeepL-backed text translation service (singleton).

    Used for ingredient recognition, food search, barcode lookup, and meal text parsing.
    Returns None if DEEPL_API_KEY is not configured.
    """
    global _deepl_text_translation_service

    if _deepl_text_translation_service is not None:
        return _deepl_text_translation_service

    if not settings.DEEPL_API_KEY:
        logger.warning("DEEPL_API_KEY not set – text translation will be skipped")
        return None

    from src.infra.adapters.deepl_translation_adapter import DeepLTranslationAdapter
    from src.domain.services.translation.deepl_text_translation_service import (
        DeepLTextTranslationService,
    )

    _deepl_text_translation_service = DeepLTextTranslationService(
        deepl_port=DeepLTranslationAdapter(settings.DEEPL_API_KEY),
    )
    logger.info("DeepL text translation service initialised")
    return _deepl_text_translation_service
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "from src.api.base_dependencies import get_deepl_text_translation_service"`
Expected: No import errors

- [ ] **Step 3: Commit**

```bash
git add src/api/base_dependencies.py
git commit -m "feat(deps): add get_deepl_text_translation_service singleton"
```

---

### Task 5: Refactor DeepLMealTranslationService to Use Core Service

**Files:**
- Modify: `src/domain/services/meal_analysis/deepl_meal_translation_service.py`
- Modify: `src/api/base_dependencies.py`

- [ ] **Step 1: Update imports and constructor**

Update `src/domain/services/meal_analysis/deepl_meal_translation_service.py`:

```python
"""
DeepL-backed meal translation service.

Translates dish_name, instructions, and ingredient names for a meal using DeepL.
Uses the core DeepLTextTranslationService internally for actual API calls.
Checks the meal_translation table first; only calls DeepL when a fully-
cached translation does not yet exist.
"""
import logging
from typing import List, Optional

from src.domain.model.meal import Meal, MealTranslation
from src.domain.model.nutrition import FoodItem
from src.domain.ports.meal_translation_repository_port import MealTranslationRepositoryPort
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
```

- [ ] **Step 2: Update translate_meal to use core service**

Replace the DeepL call (around line 94) with:

```python
            translated = await self._text_service.translate_texts(
                strings_to_translate, target_language
            )
```

Remove the old `self._deepl` references throughout the file.

- [ ] **Step 3: Update base_dependencies.py**

Update `get_deepl_meal_translation_service()` to use the text service:

```python
def get_deepl_meal_translation_service():
    """Get DeepL-backed meal translation service (singleton).

    Returns None if DEEPL_API_KEY is not configured so callers can
    treat translation as optional.
    """
    global _deepl_meal_translation_service

    if _deepl_meal_translation_service is not None:
        return _deepl_meal_translation_service

    # Requires text translation service
    text_service = get_deepl_text_translation_service()
    if text_service is None:
        logger.warning("DEEPL_API_KEY not set – meal translation will be skipped")
        return None

    from src.infra.repositories.meal_translation_repository import (
        MealTranslationRepository,
    )
    from src.domain.services.meal_analysis.deepl_meal_translation_service import (
        DeepLMealTranslationService,
    )

    _deepl_meal_translation_service = DeepLMealTranslationService(
        translation_repo=MealTranslationRepository(),
        text_translation_service=text_service,
    )
    logger.info("DeepL meal translation service initialised")
    return _deepl_meal_translation_service
```

- [ ] **Step 4: Verify syntax**

Run: `python -c "from src.domain.services.meal_analysis.deepl_meal_translation_service import DeepLMealTranslationService"`
Expected: No import errors

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/meal_analysis/deepl_meal_translation_service.py src/api/base_dependencies.py
git commit -m "refactor: DeepLMealTranslationService uses core text service"
```

---

### Task 6: Refactor DeepLSuggestionTranslationService to Use Core Service

**Files:**
- Modify: `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py`
- Modify: `src/api/base_dependencies.py`

- [ ] **Step 1: Update imports and constructor**

Update `src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py`:

```python
"""
DeepL-backed translation service for meal suggestions.

Uses the core DeepLTextTranslationService internally.
Translates meal_name, description, ingredient names, and recipe step
instructions using batched calls per suggestion.
"""
import asyncio
import logging
from dataclasses import replace as dataclasses_replace
from typing import List

from src.domain.model.meal_suggestion import MealSuggestion
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)

logger = logging.getLogger(__name__)


class DeepLSuggestionTranslationService:
    """
    Translates MealSuggestion objects via DeepL.

    Uses DeepLTextTranslationService for actual translation calls.
    Adds suggestion-specific dataclass handling on top.
    """

    def __init__(self, text_translation_service: DeepLTextTranslationService) -> None:
        self._text_service = text_translation_service
```

- [ ] **Step 2: Update translate methods to use core service**

Replace the `_deepl.translate_texts` calls with `self._text_service.translate_texts`:

In `translate_names` method:
```python
    async def translate_names(
        self, names: List[str], target_language: str
    ) -> List[str]:
        """Translate a list of meal names. Returns originals on failure."""
        if target_language == "en" or not names:
            return names
        return await self._text_service.translate_texts(names, target_language)
```

In `_translate_one` method:
```python
        translated = await self._text_service.translate_texts(strings, target_language)
```

- [ ] **Step 3: Update base_dependencies.py**

Update `get_deepl_suggestion_translation_service()`:

```python
def get_deepl_suggestion_translation_service():
    """Get DeepL-backed suggestion translation service (singleton).

    Returns None if DEEPL_API_KEY is not set (generation still works, just in English).
    """
    global _deepl_suggestion_translation_service

    if _deepl_suggestion_translation_service is not None:
        return _deepl_suggestion_translation_service

    # Requires text translation service
    text_service = get_deepl_text_translation_service()
    if text_service is None:
        logger.warning("DEEPL_API_KEY not set – suggestion translation will be skipped")
        return None

    from src.domain.services.meal_suggestion.deepl_suggestion_translation_service import (
        DeepLSuggestionTranslationService,
    )

    _deepl_suggestion_translation_service = DeepLSuggestionTranslationService(
        text_translation_service=text_service,
    )
    logger.info("DeepL suggestion translation service initialised")
    return _deepl_suggestion_translation_service
```

- [ ] **Step 4: Verify syntax**

Run: `python -c "from src.domain.services.meal_suggestion.deepl_suggestion_translation_service import DeepLSuggestionTranslationService"`
Expected: No import errors

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/meal_suggestion/deepl_suggestion_translation_service.py src/api/base_dependencies.py
git commit -m "refactor: DeepLSuggestionTranslationService uses core text service"
```

---

### Task 7: Add Translation to Ingredient Recognition Handler

**Files:**
- Modify: `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py`

- [ ] **Step 1: Add translation service dependency**

Update imports and constructor:

```python
"""
Handler for ingredient recognition command.
"""

import base64
import logging
from typing import Any, Dict, Optional

from src.app.commands.ingredient import RecognizeIngredientCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.vision_ai_service_port import VisionAIServicePort
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
from src.domain.strategies.meal_analysis_strategy import AnalysisStrategyFactory

logger = logging.getLogger(__name__)


@handles(RecognizeIngredientCommand)
class RecognizeIngredientCommandHandler(
    EventHandler[RecognizeIngredientCommand, Dict[str, Any]]
):
    """Handler for recognizing ingredients from images."""

    def __init__(
        self,
        vision_service: VisionAIServicePort = None,
        translation_service: Optional[DeepLTextTranslationService] = None,
    ):
        self.vision_service = vision_service
        self.translation_service = translation_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.vision_service = kwargs.get("vision_service", self.vision_service)
        self.translation_service = kwargs.get("translation_service", self.translation_service)
```

- [ ] **Step 2: Add translation after recognition**

Update the `handle` method to translate the result. Replace the return block (after line 85) with:

```python
            logger.info(
                f"Ingredient recognition completed: name={name}, "
                f"confidence={confidence:.2f}, category={category}"
            )

            # Translate ingredient name if non-English
            if (
                success
                and name
                and command.language != "en"
                and self.translation_service
            ):
                try:
                    translated = await self.translation_service.translate_texts(
                        [name], command.language
                    )
                    if translated and translated[0]:
                        name = translated[0]
                        logger.debug(f"Translated ingredient name to: {name}")
                except Exception as e:
                    logger.warning(f"Ingredient name translation failed: {e}")

            return {
                "name": name,
                "confidence": confidence,
                "category": category,
                "success": success,
                "message": None if success else "Could not identify ingredient",
            }
```

- [ ] **Step 3: Verify syntax**

Run: `python -c "from src.app.handlers.command_handlers.recognize_ingredient_command_handler import RecognizeIngredientCommandHandler"`
Expected: No import errors

- [ ] **Step 4: Commit**

```bash
git add src/app/handlers/command_handlers/recognize_ingredient_command_handler.py
git commit -m "feat: add DeepL translation to ingredient recognition handler"
```

---

### Task 8: Update Food Search Handler

**Files:**
- Modify: `src/app/handlers/query_handlers/search_foods_query_handler.py`

- [ ] **Step 1: Update imports and constructor**

Replace the translation_service type hint and update constructor:

```python
"""
SearchFoodsQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""

import logging
from typing import Any, Dict, List, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.domain.services.food_mapping_service import FoodMappingService
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)

logger = logging.getLogger(__name__)


@handles(SearchFoodsQuery)
class SearchFoodsQueryHandler(EventHandler[SearchFoodsQuery, Dict[str, Any]]):
    """Handler for searching foods in the database."""

    def __init__(
        self,
        cache_service,
        mapping_service: FoodMappingService,
        fat_secret_service: Optional[Any] = None,
        translation_service: Optional[DeepLTextTranslationService] = None,
    ):
        self.cache_service = cache_service
        self.mapping_service = mapping_service
        self.fat_secret_service = fat_secret_service
        self.translation_service = translation_service
```

- [ ] **Step 2: Update _search_localized method**

Replace the translation calls in `_search_localized` (lines 108-127):

```python
        # Step 2: Translation fallback — only on true empty response from localized search
        if not self.translation_service:
            try:
                results = await self.fat_secret_service.search_foods(
                    query, max_results=limit
                )
                if results:
                    await self.cache_service.cache_search(cache_key, results)
                return results
            except Exception:
                return []

        # Translate query to English using DeepL
        translated_queries = await self.translation_service.translate_to_english(
            [query], language
        )
        translated_query = translated_queries[0] if translated_queries else query

        logger.info(f"Translation fallback: '{query}' -> '{translated_query}'")

        try:
            results = await self.fat_secret_service.search_foods(
                translated_query, max_results=limit
            )
        except Exception:
            logger.warning("FatSecret EN fallback failed", exc_info=True)
            return []

        if not results:
            return []

        # Translate food names back to user's language using DeepL
        results = await self.translation_service.translate_food_names(results, language)
        await self.cache_service.cache_search(cache_key, results)
        return results
```

- [ ] **Step 3: Verify syntax**

Run: `python -c "from src.app.handlers.query_handlers.search_foods_query_handler import SearchFoodsQueryHandler"`
Expected: No import errors

- [ ] **Step 4: Commit**

```bash
git add src/app/handlers/query_handlers/search_foods_query_handler.py
git commit -m "feat: use DeepL for food search translation"
```

---

### Task 9: Update Barcode Lookup Handler

**Files:**
- Modify: `src/app/handlers/query_handlers/lookup_barcode_query_handler.py`

- [ ] **Step 1: Update imports**

Replace the translation_service type with DeepLTextTranslationService:

```python
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
```

- [ ] **Step 2: Update constructor type hint**

Change the `translation_service` parameter type:

```python
def __init__(
    self,
    open_food_facts_service: OpenFoodFactsService,
    fat_secret_service: FatSecretService,
    food_reference_repository: FoodReferenceRepository,
    translation_service: Optional[DeepLTextTranslationService] = None,
    nutritionix_service: Optional[Any] = None,
    brave_search_service: Optional[Any] = None,
    meal_generation_service: Optional[Any] = None,
    macro_validation_service: Optional[Any] = None,
):
```

- [ ] **Step 3: Verify syntax**

Run: `python -c "from src.app.handlers.query_handlers.lookup_barcode_query_handler import LookupBarcodeQueryHandler"`
Expected: No import errors

- [ ] **Step 4: Commit**

```bash
git add src/app/handlers/query_handlers/lookup_barcode_query_handler.py
git commit -m "feat: use DeepL for barcode lookup translation"
```

---

### Task 10: Update Parse Meal Text Handler

**Files:**
- Modify: `src/app/handlers/command_handlers/parse_meal_text_handler.py`

- [ ] **Step 1: Add translation service import and dependency**

Add import at top:

```python
from src.domain.services.translation.deepl_text_translation_service import (
    DeepLTextTranslationService,
)
```

Update constructor to accept translation service:

```python
@handles(ParseMealTextCommand)
class ParseMealTextHandler(
    EventHandler[ParseMealTextCommand, ParseMealTextResponseDto]
):
    """Handler for parsing meal text descriptions using Gemini."""

    def __init__(
        self,
        translation_service: Optional[DeepLTextTranslationService] = None,
    ):
        self._model_manager = GeminiModelManager.get_instance()
        self._fat_secret_service = get_fat_secret_service()
        self._translation_service = translation_service
```

- [ ] **Step 2: Replace Gemini translation with DeepL**

Replace the `_translate_english_names` method call (around line 112) with:

```python
        # Localize names for non-English users
        if command.language and command.language != "en":
            # Step 1: Strip bilingual parentheses
            for item in enhanced_items:
                item["name"] = self._extract_display_name(
                    item.get("name", "Unknown"), command.language
                )
            # Step 2: Translate any remaining English names using DeepL
            if self._translation_service:
                await self._translate_english_names_deepl(enhanced_items, command.language)
```

- [ ] **Step 3: Add new DeepL translation method**

Add this method to the class (replacing the old `_translate_english_names`):

```python
    async def _translate_english_names_deepl(
        self, items: List[Dict[str, Any]], language: str
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
                for idx, name in zip(english_indices, translated):
                    if isinstance(name, str) and name.strip():
                        items[idx]["name"] = name.strip()
            else:
                logger.warning("DeepL translation response length mismatch, skipping")
        except Exception as e:
            logger.warning(f"DeepL name translation failed, keeping English: {e}")
```

- [ ] **Step 4: Remove old Gemini translation method**

Delete the old `_translate_english_names` method (lines 211-248 approximately) that uses Gemini.

- [ ] **Step 5: Verify syntax**

Run: `python -c "from src.app.handlers.command_handlers.parse_meal_text_handler import ParseMealTextHandler"`
Expected: No import errors

- [ ] **Step 6: Commit**

```bash
git add src/app/handlers/command_handlers/parse_meal_text_handler.py
git commit -m "feat: use DeepL for meal text parsing translation"
```

---

### Task 11: Wire Services in Event Bus

**Files:**
- Modify: `src/api/dependencies/event_bus.py`

- [ ] **Step 1: Update imports in get_food_search_event_bus**

Replace the FoodSearchTranslationService import with DeepLTextTranslationService:

```python
from src.api.base_dependencies import (
    get_food_cache_service,
    get_food_data_service,
    get_food_mapping_service,
    get_open_food_facts_service_instance,
    get_fat_secret_service_instance,
    get_food_reference_repository,
    get_deepl_text_translation_service,
)
```

Remove:
```python
from src.domain.services.food_search_translation_service import (
    FoodSearchTranslationService,
)
```

- [ ] **Step 2: Update food search event bus wiring**

Replace the translation service creation (around lines 218-220):

```python
    # Translation service for localized food search (DeepL-backed)
    text_translation_service = get_deepl_text_translation_service()
```

Update the handler registrations to use the new service:

```python
    event_bus.register_handler(
        SearchFoodsQuery,
        SearchFoodsQueryHandler(
            food_cache_service,
            food_mapping_service,
            fat_secret_service=fat_secret_service,
            translation_service=text_translation_service,
        ),
    )
```

And for barcode:

```python
    event_bus.register_handler(
        LookupBarcodeQuery,
        LookupBarcodeQueryHandler(
            open_food_facts_service=open_food_facts_service,
            fat_secret_service=fat_secret_service,
            food_reference_repository=food_reference_repository,
            translation_service=text_translation_service,
            nutritionix_service=nutritionix_service,
            brave_search_service=brave_search_service,
            meal_generation_service=meal_generation_service,
            macro_validation_service=macro_validation_service,
        ),
    )
```

- [ ] **Step 3: Update configured event bus imports**

Add to the imports in `get_configured_event_bus`:

```python
from src.api.base_dependencies import (
    get_image_store,
    get_vision_service,
    get_gpt_parser,
    get_food_cache_service,
    get_food_data_service,
    get_food_mapping_service,
    get_fat_secret_service_instance,
    get_cache_service,
    get_suggestion_orchestration_service,
    get_deepl_meal_translation_service,
    get_deepl_text_translation_service,
)
```

- [ ] **Step 4: Wire ingredient recognition handler**

Update the ingredient recognition handler registration (around line 496-501):

```python
    # Get text translation service
    text_translation_service = get_deepl_text_translation_service()

    # Register ingredient recognition handler
    event_bus.register_handler(
        RecognizeIngredientCommand,
        RecognizeIngredientCommandHandler(
            vision_service=vision_service,
            translation_service=text_translation_service,
        ),
    )
```

- [ ] **Step 5: Wire parse meal text handler**

Update the ParseMealTextHandler registration (around line 368-371):

```python
    # Register meal text parsing command handler
    event_bus.register_handler(
        ParseMealTextCommand,
        ParseMealTextHandler(translation_service=text_translation_service),
    )
```

- [ ] **Step 6: Verify syntax**

Run: `python -c "from src.api.dependencies.event_bus import get_configured_event_bus, get_food_search_event_bus"`
Expected: No import errors

- [ ] **Step 7: Commit**

```bash
git add src/api/dependencies/event_bus.py
git commit -m "feat: wire DeepLTextTranslationService to all handlers"
```

---

### Task 12: Delete Deprecated Gemini Translation Service

**Files:**
- Delete: `src/domain/services/food_search_translation_service.py`

- [ ] **Step 1: Verify no other usages**

Run: `grep -r "FoodSearchTranslationService\|food_search_translation_service" --include="*.py" src/`
Expected: No matches (already replaced in event_bus.py)

- [ ] **Step 2: Delete the file**

```bash
rm src/domain/services/food_search_translation_service.py
```

- [ ] **Step 3: Commit**

```bash
git add -u src/domain/services/food_search_translation_service.py
git commit -m "chore: remove deprecated FoodSearchTranslationService"
```

---

### Task 13: Run Full Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run unit tests**

Run: `pytest tests/unit/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Run type check**

Run: `mypy src/domain/services/translation/ src/app/handlers/command_handlers/recognize_ingredient_command_handler.py`
Expected: No errors

- [ ] **Step 3: Run linting**

Run: `black src/ tests/ && ruff check src/`
Expected: No errors

- [ ] **Step 4: Final commit if any formatting changes**

```bash
git add -A
git commit -m "style: format code" || echo "No changes to commit"
```

---

## Summary

After completing all tasks:
- **Layered architecture:** Core `DeepLTextTranslationService` used by all translation
- `DeepLMealTranslationService` and `DeepLSuggestionTranslationService` refactored to use core service
- 4 additional AI flows now use DeepL: ingredient recognition, food search, barcode lookup, parse meal text
- `DeepLTranslationPort` supports bidirectional translation (EN↔target)
- Old Gemini-based `FoodSearchTranslationService` is removed
- All handlers gracefully fallback to English on translation failure
