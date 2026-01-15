"""Tests for prompt constants, including fallback meal name localization."""

import pytest
from src.domain.services.prompts.prompt_constants import (
    get_fallback_meal_name,
    LANGUAGE_NAMES,
)


class TestFallbackMealNames:
    """Test suite for get_fallback_meal_name function."""

    def test_get_fallback_meal_name_english_breakfast(self):
        """Test English breakfast fallback name."""
        assert get_fallback_meal_name("en", "breakfast", 1) == "Healthy Breakfast #1"

    def test_get_fallback_meal_name_english_lunch(self):
        """Test English lunch fallback name."""
        assert get_fallback_meal_name("en", "lunch", 2) == "Healthy Lunch #2"

    def test_get_fallback_meal_name_english_dinner(self):
        """Test English dinner fallback name."""
        assert get_fallback_meal_name("en", "dinner", 3) == "Healthy Dinner #3"

    def test_get_fallback_meal_name_english_snack(self):
        """Test English snack fallback name."""
        assert get_fallback_meal_name("en", "snack", 4) == "Healthy Snack #4"

    def test_get_fallback_meal_name_vietnamese_breakfast(self):
        """Test Vietnamese breakfast fallback name (now returns English, translated in Phase 3)."""
        # Fallback names now always return English (translation happens in Phase 3)
        assert get_fallback_meal_name("vi", "breakfast", 1) == "Healthy Breakfast #1"

    def test_get_fallback_meal_name_vietnamese_lunch(self):
        """Test Vietnamese lunch fallback name (now returns English, translated in Phase 3)."""
        assert get_fallback_meal_name("vi", "lunch", 2) == "Healthy Lunch #2"

    def test_get_fallback_meal_name_vietnamese_dinner(self):
        """Test Vietnamese dinner fallback name (now returns English, translated in Phase 3)."""
        assert get_fallback_meal_name("vi", "dinner", 3) == "Healthy Dinner #3"

    def test_get_fallback_meal_name_vietnamese_snack(self):
        """Test Vietnamese snack fallback name (now returns English, translated in Phase 3)."""
        assert get_fallback_meal_name("vi", "snack", 4) == "Healthy Snack #4"

    def test_get_fallback_meal_name_unknown_language_defaults_to_english(self):
        """Test unknown language defaults to English."""
        assert get_fallback_meal_name("xyz", "breakfast", 1) == "Healthy Breakfast #1"

    def test_get_fallback_meal_name_empty_language_defaults_to_english(self):
        """Test empty language string defaults to English."""
        assert get_fallback_meal_name("", "lunch", 1) == "Healthy Lunch #1"

    def test_get_fallback_meal_name_none_language_defaults_to_english(self):
        """Test None language defaults to English."""
        assert get_fallback_meal_name(None, "dinner", 1) == "Healthy Dinner #1"

    def test_get_fallback_meal_name_case_insensitive_language(self):
        """Test language code is case insensitive (all return English now)."""
        # All languages now return English (translation in Phase 3)
        assert get_fallback_meal_name("VI", "breakfast", 1) == "Healthy Breakfast #1"
        assert get_fallback_meal_name("En", "breakfast", 1) == "Healthy Breakfast #1"
        assert get_fallback_meal_name("VI", "LUNCH", 1) == "Healthy Lunch #1"

    def test_get_fallback_meal_name_unknown_meal_type(self):
        """Test unknown meal type uses generic format."""
        result = get_fallback_meal_name("en", "brunch", 1)
        assert result == "Healthy Brunch #1"

    def test_get_fallback_meal_name_different_indices(self):
        """Test different index values."""
        assert get_fallback_meal_name("en", "breakfast", 1) == "Healthy Breakfast #1"
        assert get_fallback_meal_name("en", "breakfast", 2) == "Healthy Breakfast #2"
        assert get_fallback_meal_name("en", "breakfast", 5) == "Healthy Breakfast #5"

    def test_get_fallback_meal_name_vietnamese_different_indices(self):
        """Test Vietnamese with different indices (all return English now)."""
        # All languages now return English (translation in Phase 3)
        assert get_fallback_meal_name("vi", "breakfast", 1) == "Healthy Breakfast #1"
        assert get_fallback_meal_name("vi", "breakfast", 2) == "Healthy Breakfast #2"
        assert get_fallback_meal_name("vi", "breakfast", 4) == "Healthy Breakfast #4"

    def test_language_names_includes_supported_languages(self):
        """Test LANGUAGE_NAMES includes all supported languages."""
        assert "en" in LANGUAGE_NAMES
        assert "vi" in LANGUAGE_NAMES
        assert LANGUAGE_NAMES["en"] == "English"
        assert LANGUAGE_NAMES["vi"] == "Vietnamese"
