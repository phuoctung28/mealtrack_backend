# DeepL Translation Unification Design

**Date:** 2026-05-05  
**Status:** Approved  
**Author:** Claude Code

## Problem

Four AI-integrated flows have inconsistent or missing translation:

| Flow | Current State | Issue |
|------|--------------|-------|
| Ingredient recognition | No translation | `language` param ignored, English-only |
| Food search | Gemini-based | Inconsistent with DeepL used elsewhere |
| Barcode lookup | Gemini-based | Inconsistent with DeepL used elsewhere |
| Parse meal text | Gemini inline | Inconsistent, higher token cost |

Meal scan and meal suggestions already use DeepL correctly.

## Solution

Create a unified `DeepLTextTranslationService` for simple text translation across all flows.

### Architecture

**New file:** `src/domain/services/translation/deepl_text_translation_service.py`

```python
class DeepLTextTranslationService:
    def __init__(self, deepl_port: DeepLTranslationPort) -> None: ...
    
    async def translate_texts(
        self, texts: List[str], target_lang: str
    ) -> List[str]:
        """Translate texts from English to target language."""
    
    async def translate_to_english(
        self, texts: List[str], source_lang: str
    ) -> List[str]:
        """Translate texts from source language to English (for search queries)."""
    
    async def translate_food_names(
        self, foods: List[Dict[str, Any]], target_lang: str
    ) -> List[Dict[str, Any]]:
        """Translate food name/description fields, preserving originals."""
```

### Port Enhancement

Add reverse translation method to `DeepLTranslationPort`:

```python
@abstractmethod
async def translate_to_english(self, texts: List[str], source_lang: str) -> List[str]:
    """Translate from source language to English."""
```

Implement in `DeepLTranslationAdapter`:
- `target_lang="EN-US"`
- `source_lang` mapped via `_LANG_MAP` (same as existing mapping)
- If `source_lang` is unknown, use DeepL auto-detect (`source_lang=None`)

### Handler Changes

#### 1. Ingredient Recognition (`recognize_ingredient_command_handler.py`)

- Add `DeepLTextTranslationService` dependency
- After Gemini returns result, translate `name` if `command.language != "en"`

```python
# After getting result from vision service
if command.language != "en" and result.get("name"):
    translated = await self.translation_service.translate_texts(
        [result["name"]], command.language
    )
    result["name"] = translated[0]
```

#### 2. Food Search (`search_foods_query_handler.py`)

- Replace `FoodSearchTranslationService` with `DeepLTextTranslationService`
- Use `translate_to_english()` for query translation
- Use `translate_food_names()` for results

#### 3. Barcode Lookup (`lookup_barcode_query_handler.py`)

- Swap `translation_service` to `DeepLTextTranslationService`
- `_maybe_translate()` continues using `translate_food_names()`

#### 4. Parse Meal Text (`parse_meal_text_handler.py`)

- Replace `_translate_english_names()` method with call to `DeepLTextTranslationService.translate_texts()`
- Remove inline Gemini translation code (lines 228-248)

### Dependency Injection

Add singleton in `src/api/base_dependencies.py`:

```python
_deepl_text_translation_service = None

def get_deepl_text_translation_service():
    global _deepl_text_translation_service
    if _deepl_text_translation_service is not None:
        return _deepl_text_translation_service
    
    from src.infra.adapters.deepl_translation_adapter import DeepLTranslationAdapter
    from src.domain.services.translation.deepl_text_translation_service import (
        DeepLTextTranslationService,
    )
    
    _deepl_text_translation_service = DeepLTextTranslationService(
        deepl_port=DeepLTranslationAdapter(settings.DEEPL_API_KEY),
    )
    return _deepl_text_translation_service
```

### Error Handling

- All translation calls wrapped in try/except
- On failure: log warning, return original/English content
- Never block main flow due to translation failure
- No retries (DeepL is reliable)

### Deprecation

After migration, delete:
- `src/domain/services/food_search_translation_service.py`

## Testing

**Unit tests:**
- `tests/unit/domain/services/test_deepl_text_translation_service.py`
- Mock `DeepLTranslationPort`, verify batching and fallback behavior
- Update handler tests to verify translation integration

**Integration tests:**
- Skip if `DEEPL_API_KEY` not set
- Test round-trip translation

## Files Changed

**New:**
- `src/domain/services/translation/__init__.py`
- `src/domain/services/translation/deepl_text_translation_service.py`
- `tests/unit/domain/services/test_deepl_text_translation_service.py`

**Modified:**
- `src/domain/ports/deepl_translation_port.py` — add `translate_to_english()`
- `src/infra/adapters/deepl_translation_adapter.py` — implement `translate_to_english()`
- `src/api/base_dependencies.py` — add singleton
- `src/app/handlers/command_handlers/recognize_ingredient_command_handler.py`
- `src/app/handlers/query_handlers/search_foods_query_handler.py`
- `src/app/handlers/query_handlers/lookup_barcode_query_handler.py`
- `src/app/handlers/command_handlers/parse_meal_text_handler.py`
- `src/api/dependencies/event_bus.py` — wire new service

**Deleted:**
- `src/domain/services/food_search_translation_service.py`
