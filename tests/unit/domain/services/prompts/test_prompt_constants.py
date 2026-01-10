"""Tests for prompt constants, including fallback meal name localization."""

import pytest
from src.domain.services.prompts.prompt_constants import (
    get_fallback_meal_name,
    FALLBACK_MEAL_NAMES,
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
        """Test Vietnamese breakfast fallback name."""
        assert get_fallback_meal_name("vi", "breakfast", 1) == "Bữa sáng lành mạnh #1"

    def test_get_fallback_meal_name_vietnamese_lunch(self):
        """Test Vietnamese lunch fallback name."""
        assert get_fallback_meal_name("vi", "lunch", 2) == "Bữa trưa lành mạnh #2"

    def test_get_fallback_meal_name_vietnamese_dinner(self):
        """Test Vietnamese dinner fallback name."""
        assert get_fallback_meal_name("vi", "dinner", 3) == "Bữa tối lành mạnh #3"

    def test_get_fallback_meal_name_vietnamese_snack(self):
        """Test Vietnamese snack fallback name."""
        assert get_fallback_meal_name("vi", "snack", 4) == "Bữa phụ lành mạnh #4"

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
        """Test language code is case insensitive."""
        assert get_fallback_meal_name("VI", "breakfast", 1) == "Bữa sáng lành mạnh #1"
        assert get_fallback_meal_name("En", "breakfast", 1) == "Healthy Breakfast #1"
        assert get_fallback_meal_name("VI", "LUNCH", 1) == "Bữa trưa lành mạnh #1"

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
        """Test Vietnamese with different indices."""
        assert get_fallback_meal_name("vi", "breakfast", 1) == "Bữa sáng lành mạnh #1"
        assert get_fallback_meal_name("vi", "breakfast", 2) == "Bữa sáng lành mạnh #2"
        assert get_fallback_meal_name("vi", "breakfast", 4) == "Bữa sáng lành mạnh #4"

    def test_fallback_meal_names_dictionary_structure(self):
        """Test FALLBACK_MEAL_NAMES dictionary has correct structure."""
        assert "en" in FALLBACK_MEAL_NAMES
        assert "vi" in FALLBACK_MEAL_NAMES

        # Check English meals
        en_meals = FALLBACK_MEAL_NAMES["en"]
        assert "breakfast" in en_meals
        assert "lunch" in en_meals
        assert "dinner" in en_meals
        assert "snack" in en_meals

        # Check Vietnamese meals
        vi_meals = FALLBACK_MEAL_NAMES["vi"]
        assert "breakfast" in vi_meals
        assert "lunch" in vi_meals
        assert "dinner" in vi_meals
        assert "snack" in vi_meals

    def test_language_names_includes_supported_languages(self):
        """Test LANGUAGE_NAMES includes all supported languages."""
        assert "en" in LANGUAGE_NAMES
        assert "vi" in LANGUAGE_NAMES
        assert LANGUAGE_NAMES["en"] == "English"
        assert LANGUAGE_NAMES["vi"] == "Vietnamese"
