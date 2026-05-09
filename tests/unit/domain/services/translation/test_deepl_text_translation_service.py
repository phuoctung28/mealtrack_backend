"""Tests for DeepLTextTranslationService."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.services.translation.deepl_text_translation_service import DeepLTextTranslationService


@pytest.fixture
def deepl_port():
    port = MagicMock()
    port.translate_texts = AsyncMock()
    port.translate_to_english = AsyncMock()
    return port


@pytest.fixture
def service(deepl_port):
    return DeepLTextTranslationService(deepl_port=deepl_port)


# ─────────────────────────── translate_texts ───────────────────────────

class TestTranslateTexts:
    @pytest.mark.asyncio
    async def test_translates_to_target_language(self, service, deepl_port):
        deepl_port.translate_texts.return_value = ["Poulet", "Riz"]
        result = await service.translate_texts(["Chicken", "Rice"], "fr")
        assert result == ["Poulet", "Riz"]
        deepl_port.translate_texts.assert_awaited_once_with(["Chicken", "Rice"], "fr")

    @pytest.mark.asyncio
    async def test_returns_original_for_english_target(self, service, deepl_port):
        result = await service.translate_texts(["Chicken", "Rice"], "en")
        assert result == ["Chicken", "Rice"]
        deepl_port.translate_texts.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self, service, deepl_port):
        result = await service.translate_texts([], "vi")
        assert result == []
        deepl_port.translate_texts.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_original_on_error(self, service, deepl_port):
        deepl_port.translate_texts.side_effect = Exception("DeepL down")
        result = await service.translate_texts(["Chicken", "Rice"], "vi")
        assert result == ["Chicken", "Rice"]


# ─────────────────────────── translate_to_english ───────────────────────────

class TestTranslateToEnglish:
    @pytest.mark.asyncio
    async def test_translates_to_english(self, service, deepl_port):
        deepl_port.translate_to_english.return_value = ["Chicken", "Rice"]
        result = await service.translate_to_english(["Gà", "Cơm"], "vi")
        assert result == ["Chicken", "Rice"]
        deepl_port.translate_to_english.assert_awaited_once_with(["Gà", "Cơm"], "vi")

    @pytest.mark.asyncio
    async def test_returns_original_for_english_source(self, service, deepl_port):
        result = await service.translate_to_english(["Chicken", "Rice"], "en")
        assert result == ["Chicken", "Rice"]
        deepl_port.translate_to_english.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self, service, deepl_port):
        result = await service.translate_to_english([], "vi")
        assert result == []
        deepl_port.translate_to_english.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_original_on_error(self, service, deepl_port):
        deepl_port.translate_to_english.side_effect = Exception("DeepL down")
        result = await service.translate_to_english(["Gà", "Cơm"], "vi")
        assert result == ["Gà", "Cơm"]


# ─────────────────────────── translate_food_names ───────────────────────────

class TestTranslateFoodNames:
    @pytest.mark.asyncio
    async def test_translates_food_name_and_description_fields(self, service, deepl_port):
        foods = [
            {"name": "Chicken breast", "description": "Chicken breast"},
            {"name": "Brown rice", "description": "Brown rice"},
        ]
        deepl_port.translate_texts.return_value = ["Ức gà", "Cơm gạo lứt"]
        result = await service.translate_food_names(foods, "vi")
        assert result[0]["name"] == "Ức gà"
        assert result[0]["name_original"] == "Chicken breast"
        assert result[0]["description"] == "Ức gà"
        assert result[0]["description_original"] == "Chicken breast"
        assert result[1]["name"] == "Cơm gạo lứt"
        assert result[1]["name_original"] == "Brown rice"

    @pytest.mark.asyncio
    async def test_preserves_originals_as_separate_keys(self, service, deepl_port):
        foods = [{"name": "Chicken breast", "description": "Grilled chicken"}]
        deepl_port.translate_texts.return_value = ["Ức gà nướng"]
        result = await service.translate_food_names(foods, "vi")
        # description takes precedence for unique name extraction
        assert result[0]["description_original"] == "Grilled chicken"
        assert result[0]["description"] == "Ức gà nướng"

    @pytest.mark.asyncio
    async def test_skips_translation_for_english_target(self, service, deepl_port):
        foods = [{"name": "Chicken", "description": "Grilled chicken"}]
        result = await service.translate_food_names(foods, "en")
        assert result == foods
        deepl_port.translate_texts.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_unchanged_on_error(self, service, deepl_port):
        foods = [{"name": "Chicken breast", "description": "Chicken breast"}]
        deepl_port.translate_texts.side_effect = Exception("DeepL down")
        result = await service.translate_food_names(foods, "vi")
        assert result == foods
        assert "name_original" not in result[0]

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_empty_foods(self, service, deepl_port):
        result = await service.translate_food_names([], "vi")
        assert result == []
        deepl_port.translate_texts.assert_not_called()

    @pytest.mark.asyncio
    async def test_pads_when_deepl_returns_fewer_items(self, service, deepl_port):
        foods = [
            {"name": "Chicken", "description": "Chicken"},
            {"name": "Rice", "description": "Rice"},
        ]
        # DeepL returns only one item instead of two
        deepl_port.translate_texts.return_value = ["Gà"]
        result = await service.translate_food_names(foods, "vi")
        assert result[0]["name"] == "Gà"
        # Second item padded with original
        assert result[1]["name"] == "Rice"

    @pytest.mark.asyncio
    async def test_deduplicates_names_before_translating(self, service, deepl_port):
        foods = [
            {"name": "Chicken", "description": "Chicken"},
            {"name": "Chicken", "description": "Chicken"},
        ]
        deepl_port.translate_texts.return_value = ["Gà"]
        result = await service.translate_food_names(foods, "vi")
        # Should only call DeepL once with deduplicated list
        deepl_port.translate_texts.assert_awaited_once_with(["Chicken"], "vi")
        assert result[0]["name"] == "Gà"
        assert result[1]["name"] == "Gà"
