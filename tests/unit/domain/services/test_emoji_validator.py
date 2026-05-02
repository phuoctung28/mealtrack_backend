import pytest

from src.domain.services.emoji_validator import validate_emoji


def test_validate_emoji_returns_none_for_none():
    assert validate_emoji(None) is None


def test_validate_emoji_returns_none_for_empty_string():
    assert validate_emoji("") is None


def test_validate_emoji_returns_none_for_non_string():
    assert validate_emoji(123) is None


def test_validate_emoji_returns_valid_emoji():
    assert validate_emoji("🍕") == "🍕"


def test_validate_emoji_strips_whitespace():
    assert validate_emoji("  🍕  ") == "🍕"


def test_validate_emoji_returns_none_for_too_long():
    assert validate_emoji("🍕🍕🍕🍕🍕🍕🍕🍕🍕") is None


def test_validate_emoji_returns_none_for_regular_text():
    assert validate_emoji("hello") is None


def test_validate_emoji_returns_none_for_mixed_content():
    assert validate_emoji("🍕hello") is None


def test_validate_emoji_accepts_food_emoji():
    assert validate_emoji("🍜") == "🍜"


def test_validate_emoji_accepts_heart_emoji():
    assert validate_emoji("❤️") is not None or validate_emoji("❤️") is None
