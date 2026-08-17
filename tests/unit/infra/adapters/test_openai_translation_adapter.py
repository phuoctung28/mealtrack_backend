import asyncio
from unittest.mock import AsyncMock

import pytest

from src.domain.model.translation_result import TranslationOutcome
from src.infra.adapters.openai_translation_adapter import OpenAITranslationAdapter
from src.infra.services.ai.openai_structured_generation_result import (
    OpenAIStructuredGenerationResult,
)
from src.infra.services.ai.openai_translation_schemas import (
    OpenAITranslationBatch,
    OpenAITranslationItem,
)


@pytest.mark.asyncio
async def test_adapter_reconstructs_order_and_forces_non_storage():
    provider = AsyncMock()
    provider.generate_structured_result.return_value = OpenAIStructuredGenerationResult(
        parsed=OpenAITranslationBatch(
            items=[
                OpenAITranslationItem(index=1, text="Riz"),
                OpenAITranslationItem(index=0, text="Poulet"),
            ]
        )
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")

    result = await adapter.translate_texts(
        ["Chicken", "Rice"], source_language="en", target_language="fr"
    )

    assert result.outcome is TranslationOutcome.TRANSLATED
    assert result.items == ("Poulet", "Riz")
    call = provider.generate_structured_result.await_args.kwargs
    assert call["store_responses"] is False


@pytest.mark.asyncio
async def test_adapter_rejects_duplicate_indexes_without_partial_cache_result():
    provider = AsyncMock()
    provider.generate_structured_result.return_value = OpenAIStructuredGenerationResult(
        parsed=OpenAITranslationBatch(
            items=[
                OpenAITranslationItem(index=0, text="Poulet"),
                OpenAITranslationItem(index=0, text="Riz"),
            ]
        )
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")
    result = await adapter.translate_texts(["Chicken", "Rice"], "en", "fr")
    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert result.items == ("Chicken", "Rice")


@pytest.mark.asyncio
async def test_adapter_never_marks_incomplete_full_index_output_translated():
    provider = AsyncMock()
    provider.generate_structured_result.return_value = OpenAIStructuredGenerationResult(
        parsed=OpenAITranslationBatch(
            items=[
                OpenAITranslationItem(index=0, text="Poulet"),
                OpenAITranslationItem(index=1, text="Riz"),
            ]
        ),
        incomplete=True,
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")

    result = await adapter.translate_texts(["Chicken", "Rice"], "en", "fr")

    assert result.outcome is TranslationOutcome.PARTIAL
    assert result.items == ("Poulet", "Riz")


@pytest.mark.asyncio
async def test_adapter_maps_translation_deadline_to_unavailable():
    provider = AsyncMock()

    async def wait_forever(**kwargs):
        await asyncio.sleep(1)

    provider.generate_structured_result.side_effect = wait_forever
    adapter = OpenAITranslationAdapter(
        provider=provider,
        model="translation-model",
        timeout_seconds=0.01,
    )

    result = await adapter.translate_texts(["Chicken"], "en", "fr")

    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert result.items == ("Chicken",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "candidate", "target"),
    [
        ("Coca-Cola 330 ml", "Pepsi 330 kg", "fr"),
        ("Nutella 20 g", "Nocilla 20 g", "fr"),
        ("Use 120 grams of rice", "Use 120 pounds of rice", "fr"),
        ("5 min", "5 kg", "fr"),
        ("Use 1 cup and 2 grams", "Usa 1 gramo y 2 tazas", "es"),
        ("Add {water} ml and {salt} g", "Añade {water} g y {salt} ml", "es"),
        ("Chicken", "Chicken", "fr"),
    ],
)
async def test_adapter_rejects_structurally_unsafe_or_unchanged_output(
    source, candidate, target
):
    provider = AsyncMock()
    provider.generate_structured_result.return_value = (
        OpenAIStructuredGenerationResult(
            parsed=OpenAITranslationBatch(
                items=[OpenAITranslationItem(index=0, text=candidate)]
            )
        )
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")

    result = await adapter.translate_texts([source], "en", target)

    assert result.outcome is TranslationOutcome.PARTIAL
    assert result.items == (source,)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "candidate", "target"),
    [
        ("Milk chocolate", "Chocolate con leche", "es"),
        ("Coca-Cola chicken", "Poulet Coca-Cola", "fr"),
        ("Nutella toast", "Toast au Nutella", "fr"),
        ("Beef burger", "Beef-Burger", "de"),
    ],
)
async def test_adapter_accepts_valid_loanwords_and_reordered_brands(
    source, candidate, target
):
    provider = AsyncMock()
    provider.generate_structured_result.return_value = (
        OpenAIStructuredGenerationResult(
            parsed=OpenAITranslationBatch(
                items=[OpenAITranslationItem(index=0, text=candidate)]
            )
        )
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")

    result = await adapter.translate_texts([source], "en", target)

    assert result.outcome is TranslationOutcome.TRANSLATED
    assert result.items == (candidate,)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "candidate", "target"),
    [
        ("Use 120 grams of rice", "Usa 120 gramos de arroz", "es"),
        ("Cook for 15 minutes", "Nấu trong 15 phút", "vi"),
        ("Add 0.5 cup", "加入 0.5杯", "zh"),
        ("Add 1 tablespoon", "Añade 1 cucharada", "es"),
        ("Add 1 tablespoon", "大さじ 1", "ja"),
        ("Wait 1 second", "Espera 1 segundo", "es"),
        ("Use 2 kilograms", "使用 2 公斤", "zh"),
        ("Use 2 cups", "Usa 2 tazas", "es"),
        ("Mix thoroughly", "充分混合", "zh"),
        ("Mix thoroughly", "十分に混ぜる", "ja"),
        ("Use 1 piece", "鶏肉を1個使う", "ja"),
        ("Use 1 slice", "使用 1 片", "zh"),
        ("Use 1 serving", "使用 1 份", "zh"),
        ("Use 1 piece", "Dùng 1 miếng", "vi"),
        ("Use 1 serving", "Dùng 1 phần", "vi"),
        ("Use 1 piece", "Usa 1 pieza", "es"),
        ("Use 1 slice", "Utilisez 1 tranche", "fr"),
        ("Use 1 serving", "Verwende 1 Portion", "de"),
        ("Breakfast 1", "Frühstück 1", "de"),
        ("Ratio 1 to 2", "Proportion 1 à 2", "fr"),
        ("Ratio 1 to 2", "Proporción 1 a 2", "es"),
    ],
)
async def test_adapter_accepts_localized_equivalent_units(source, candidate, target):
    provider = AsyncMock()
    provider.generate_structured_result.return_value = (
        OpenAIStructuredGenerationResult(
            parsed=OpenAITranslationBatch(
                items=[OpenAITranslationItem(index=0, text=candidate)]
            )
        )
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")

    result = await adapter.translate_texts([source], "en", target)

    assert result.outcome is TranslationOutcome.TRANSLATED
    assert result.items == (candidate,)


@pytest.mark.asyncio
async def test_adapter_allows_reverse_translation_to_english_food_terms():
    provider = AsyncMock()
    provider.generate_structured_result.return_value = (
        OpenAIStructuredGenerationResult(
            parsed=OpenAITranslationBatch(
                items=[OpenAITranslationItem(index=0, text="chicken")]
            )
        )
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")

    result = await adapter.translate_texts(["gà"], "vi", "en")

    assert result.outcome is TranslationOutcome.TRANSLATED
    assert result.items == ("chicken",)


@pytest.mark.asyncio
async def test_adapter_allows_invariant_only_brand_output():
    provider = AsyncMock()
    provider.generate_structured_result.return_value = (
        OpenAIStructuredGenerationResult(
            parsed=OpenAITranslationBatch(
                items=[OpenAITranslationItem(index=0, text="Coca-Cola")]
            )
        )
    )
    adapter = OpenAITranslationAdapter(provider=provider, model="translation-model")

    result = await adapter.translate_texts(["Coca-Cola"], "en", "fr")

    assert result.outcome is TranslationOutcome.TRANSLATED
    assert result.items == ("Coca-Cola",)
