"""Tests for meal suggestion request schemas."""

from src.api.schemas.request.meal_suggestion_requests import (
    MealSuggestionRequest,
    MealSizeEnum,
    MealPortionTypeEnum,
    CookingTimeEnum,
    map_legacy_size_to_type,
)


class TestMealPortionTypeMapping:
    """Test legacy size to new type mapping."""

    def test_s_maps_to_snack(self):
        assert map_legacy_size_to_type(MealSizeEnum.S) == MealPortionTypeEnum.SNACK

    def test_m_maps_to_snack(self):
        assert map_legacy_size_to_type(MealSizeEnum.M) == MealPortionTypeEnum.SNACK

    def test_l_maps_to_main(self):
        assert map_legacy_size_to_type(MealSizeEnum.L) == MealPortionTypeEnum.MAIN

    def test_xl_maps_to_main(self):
        assert map_legacy_size_to_type(MealSizeEnum.XL) == MealPortionTypeEnum.MAIN

    def test_omad_maps_to_omad(self):
        assert map_legacy_size_to_type(MealSizeEnum.OMAD) == MealPortionTypeEnum.OMAD


class TestMealSuggestionRequest:
    """Test request validation and defaults."""

    def test_new_portion_type_preferred(self):
        req = MealSuggestionRequest(
            meal_type="lunch",
            meal_portion_type=MealPortionTypeEnum.MAIN,
            meal_size=MealSizeEnum.S,  # Legacy
            cooking_time_minutes=CookingTimeEnum.MEDIUM,
        )
        # New field takes precedence
        assert req.get_effective_portion_type() == MealPortionTypeEnum.MAIN

    def test_legacy_size_fallback(self):
        req = MealSuggestionRequest(
            meal_type="lunch",
            meal_size=MealSizeEnum.L,
            cooking_time_minutes=CookingTimeEnum.MEDIUM,
        )
        assert req.get_effective_portion_type() == MealPortionTypeEnum.MAIN

    def test_default_based_on_meal_type_snack(self):
        req = MealSuggestionRequest(
            meal_type="snack",
            cooking_time_minutes=CookingTimeEnum.QUICK,
        )
        assert req.get_effective_portion_type() == MealPortionTypeEnum.SNACK

    def test_default_based_on_meal_type_lunch(self):
        req = MealSuggestionRequest(
            meal_type="lunch",
            cooking_time_minutes=CookingTimeEnum.MEDIUM,
        )
        assert req.get_effective_portion_type() == MealPortionTypeEnum.MAIN

    def test_default_based_on_meal_type_breakfast(self):
        req = MealSuggestionRequest(
            meal_type="breakfast",
            cooking_time_minutes=CookingTimeEnum.MEDIUM,
        )
        assert req.get_effective_portion_type() == MealPortionTypeEnum.MAIN

    def test_default_based_on_meal_type_dinner(self):
        req = MealSuggestionRequest(
            meal_type="dinner",
            cooking_time_minutes=CookingTimeEnum.STANDARD,
        )
        assert req.get_effective_portion_type() == MealPortionTypeEnum.MAIN
