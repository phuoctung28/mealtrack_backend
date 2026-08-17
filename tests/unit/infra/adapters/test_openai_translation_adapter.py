from unittest.mock import AsyncMock

import pytest

from src.infra.adapters.openai_translation_adapter import (
    OpenAITranslationAdapter,
    TranslationBatch,
)


def _adapter(provider=None):
    return OpenAITranslationAdapter(
        provider=provider or AsyncMock(),
        model="gpt-test",
        timeout_seconds=1,
    )


@pytest.mark.asyncio
async def test_skips_provider_for_empty_and_english_input():
    provider = AsyncMock()
    adapter = _adapter(provider)

    assert await adapter.translate_texts([], "vi") == []
    assert await adapter.translate_texts(["keep"], "en") == ["keep"]
    provider.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_translates_indexed_batch_with_openai_structured_output():
    provider = AsyncMock()
    provider.generate.return_value = {
        "items": [
            {"index": 0, "text": "Ức gà"},
            {"index": 1, "text": "Cơm"},
        ]
    }
    adapter = _adapter(provider)

    result = await adapter.translate_texts(["Chicken breast", "Rice"], "vi")

    assert result == ["Ức gà", "Cơm"]
    provider.generate.assert_awaited_once()
    kwargs = provider.generate.call_args.kwargs
    assert kwargs["model"] == "gpt-test"
    assert kwargs["purpose_hint"] == "translation"
    assert kwargs["schema"] is TranslationBatch
    assert "faithfully and naturally" in kwargs["system_message"]
    assert "do not explain, summarize" in kwargs["system_message"]
    assert "Do not leave an English food ingredient unchanged" in kwargs[
        "system_message"
    ]


@pytest.mark.asyncio
async def test_preserves_input_order_and_falls_back_for_missing_items():
    provider = AsyncMock()
    provider.generate.return_value = {"items": [{"index": 1, "text": "Cơm"}]}
    adapter = _adapter(provider)

    result = await adapter.translate_texts(["Chicken", "Rice"], "vi")

    assert result == ["Chicken", "Cơm"]


@pytest.mark.asyncio
async def test_repairs_missing_items_in_a_partial_batch():
    provider = AsyncMock()
    provider.generate.side_effect = [
        {"items": [{"index": 1, "text": "Cơm"}]},
        {
            "items": [
                {"index": 0, "text": "Ức gà"},
                {"index": 2, "text": "Bông cải"},
            ]
        },
    ]
    adapter = _adapter(provider)

    result = await adapter.translate_texts(
        ["Chicken breast", "Rice", "Broccoli"], "vi"
    )

    assert result == ["Ức gà", "Cơm", "Bông cải"]
    assert provider.generate.await_count == 2


@pytest.mark.asyncio
async def test_repairs_an_unchanged_english_ingredient():
    provider = AsyncMock()
    provider.generate.side_effect = [
        {
            "items": [
                {"index": 0, "text": "Bread"},
                {"index": 1, "text": "Thịt heo"},
            ]
        },
        {"items": [{"index": 0, "text": "Bánh mì"}]},
    ]
    adapter = _adapter(provider)

    result = await adapter.translate_texts(["Bread", "Pork"], "vi")

    assert result == ["Bánh mì", "Thịt heo"]
    assert provider.generate.await_count == 2


@pytest.mark.asyncio
async def test_rejects_numeric_token_changes():
    provider = AsyncMock()
    provider.generate.return_value = {"items": [{"index": 0, "text": "Hai trăm gam"}]}
    adapter = _adapter(provider)

    result = await adapter.translate_texts(["200 g chicken"], "vi")

    assert result == ["200 g chicken"]


@pytest.mark.asyncio
async def test_returns_originals_when_openai_fails():
    provider = AsyncMock()
    provider.generate.side_effect = RuntimeError("provider unavailable")
    adapter = _adapter(provider)

    result = await adapter.translate_to_english(["Gà", "Cơm"], "vi")

    assert result == ["Gà", "Cơm"]
