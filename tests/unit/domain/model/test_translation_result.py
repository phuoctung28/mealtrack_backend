from src.domain.model.translation_result import TranslationOutcome, TranslationResult


def test_translation_result_is_immutable_and_only_full_translation_is_cacheable():
    result = TranslationResult(
        texts=("Poulet", "Riz"),
        outcome=TranslationOutcome.TRANSLATED,
        source_language="en",
        target_language="fr",
    )

    assert result.items == ("Poulet", "Riz")
    assert result.cacheable is True
    assert result.to_list() == ["Poulet", "Riz"]

    try:
        result.texts = ("x", "y")
    except Exception:
        pass
    else:
        raise AssertionError("TranslationResult must be immutable")


def test_canonical_result_is_not_cacheable():
    result = TranslationResult.unavailable(
        ["Chicken"], source_language="en", target_language="vi"
    )
    assert result.outcome is TranslationOutcome.UNAVAILABLE
    assert result.to_list() == ["Chicken"]
    assert result.cacheable is False

