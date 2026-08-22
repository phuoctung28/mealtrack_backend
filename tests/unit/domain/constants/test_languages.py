from src.domain.constants.languages import (
    DEFAULT_LANGUAGE,
    SUPPORTED_TRANSLATION_LANGUAGES,
    is_supported_language,
    is_supported_translation_pair,
    normalize_language,
)


def test_translation_languages_are_exact_and_normalized():
    assert SUPPORTED_TRANSLATION_LANGUAGES == frozenset({"en", "vi", "es", "fr", "de", "ja", "zh"})
    assert normalize_language("VI-vn") == "vi"
    assert normalize_language(None) == DEFAULT_LANGUAGE
    assert is_supported_language("ja")
    assert not is_supported_language("ko")


def test_translation_pair_requires_supported_locales():
    assert is_supported_translation_pair("en", "vi")
    assert is_supported_translation_pair("vi-VN", "en-US")
    assert not is_supported_translation_pair("ko", "en")

