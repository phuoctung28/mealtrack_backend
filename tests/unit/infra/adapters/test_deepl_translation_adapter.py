import pytest
from unittest.mock import Mock

import deepl

from src.infra.adapters.deepl_translation_adapter import (
    SOURCE_LANG,
    DeepLTranslationAdapter,
)


def test_init_requires_api_key():
    with pytest.raises(ValueError):
        DeepLTranslationAdapter(api_key="")


@pytest.mark.asyncio
async def test_translate_texts_skips_api_when_target_is_english():
    adapter = DeepLTranslationAdapter.__new__(DeepLTranslationAdapter)
    adapter._translator = Mock()

    result = await adapter.translate_texts(["keep", "me"], "en")
    assert result == ["keep", "me"]
    result_en = await adapter.translate_texts(["a"], "EN")
    assert result_en == ["a"]
    adapter._translator.translate_text.assert_not_called()


@pytest.mark.asyncio
async def test_translate_texts_returns_empty_list_for_empty_input(monkeypatch):
    # Avoid constructing real SDK translator
    adapter = DeepLTranslationAdapter.__new__(DeepLTranslationAdapter)
    adapter._translator = Mock()

    result = await adapter.translate_texts([], "vi")
    assert result == []
    adapter._translator.translate_text.assert_not_called()


@pytest.mark.asyncio
async def test_translate_texts_maps_language_and_flattens_list_results(monkeypatch):
    adapter = DeepLTranslationAdapter.__new__(DeepLTranslationAdapter)

    class _R:
        def __init__(self, text):
            self.text = text

    adapter._translator = Mock()
    adapter._translator.translate_text = Mock(return_value=[_R("a"), _R("b")])

    async def fake_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr("src.infra.adapters.deepl_translation_adapter.asyncio.to_thread", fake_to_thread)

    result = await adapter.translate_texts(["x", "y"], "vi")
    assert result == ["a", "b"]
    adapter._translator.translate_text.assert_called_once()
    _, kwargs = adapter._translator.translate_text.call_args
    assert kwargs["target_lang"] == "VI"
    assert kwargs["source_lang"] == SOURCE_LANG


@pytest.mark.asyncio
async def test_translate_texts_flattens_single_result(monkeypatch):
    adapter = DeepLTranslationAdapter.__new__(DeepLTranslationAdapter)

    class _R:
        def __init__(self, text):
            self.text = text

    adapter._translator = Mock()
    adapter._translator.translate_text = Mock(return_value=_R("only"))

    async def fake_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr("src.infra.adapters.deepl_translation_adapter.asyncio.to_thread", fake_to_thread)

    result = await adapter.translate_texts(["x"], "pt")
    assert result == ["only"]
    _, kwargs = adapter._translator.translate_text.call_args
    assert kwargs["target_lang"] == "PT-BR"
    assert kwargs["source_lang"] == SOURCE_LANG


@pytest.mark.asyncio
async def test_translate_texts_raises_on_deepl_exception(monkeypatch):
    adapter = DeepLTranslationAdapter.__new__(DeepLTranslationAdapter)
    adapter._translator = Mock()

    def raise_exc(*args, **kwargs):
        raise deepl.DeepLException("boom")

    adapter._translator.translate_text = Mock(side_effect=raise_exc)

    async def fake_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr("src.infra.adapters.deepl_translation_adapter.asyncio.to_thread", fake_to_thread)

    with pytest.raises(deepl.DeepLException):
        await adapter.translate_texts(["x"], "vi")

