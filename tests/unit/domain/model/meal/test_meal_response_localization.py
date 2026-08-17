from datetime import datetime

import pytest

from src.domain.constants.languages import SUPPORTED_TRANSLATION_LANGUAGES
from src.domain.model.meal import Meal, MealImage, MealStatus
from src.domain.model.meal.meal_response_localization import (
    parse_meal_response_localization,
    persist_meal_response_localization,
)
from src.domain.model.nutrition import FoodItem, Macros, Nutrition

LOCALIZED_NAMES = {
    "de": ("Reisnudelsuppe", "Reisnudeln"),
    "es": ("Sopa de fideos de arroz", "Fideos de arroz"),
    "fr": ("Soupe de nouilles de riz", "Nouilles de riz"),
    "ja": ("米麺スープ", "米麺"),
    "vi": ("Bún nước", "Bún gạo"),
    "zh": ("米粉汤", "米粉"),
}


def _structured_data() -> dict:
    return {
        "dish_name": "Rice noodle soup",
        "localized_language": "vi",
        "localized_dish_name": "Bún nước",
        "foods": [
            {
                "name": "Rice noodles",
                "localized_name": "Bún gạo",
            }
        ],
    }


def test_extracts_localized_fields_without_replacing_canonical_values():
    result = parse_meal_response_localization(
        _structured_data(),
        "vi-VN",
        expected_food_count=1,
    )

    assert result is not None
    assert result.language == "vi"
    assert result.dish_name == "Bún nước"
    assert result.food_item_names == ("Bún gạo",)
    assert _structured_data()["dish_name"] == "Rice noodle soup"
    assert _structured_data()["foods"][0]["name"] == "Rice noodles"


def test_english_request_does_not_require_localized_fields():
    assert (
        parse_meal_response_localization(
            {"dish_name": "Rice noodle soup", "foods": [{"name": "Rice noodles"}]},
            "en",
            expected_food_count=1,
        )
        is None
    )


@pytest.mark.parametrize("language", sorted(SUPPORTED_TRANSLATION_LANGUAGES - {"en"}))
def test_persists_every_supported_localized_language_without_changing_nutrition(
    language,
):
    localized_dish, localized_food = LOCALIZED_NAMES[language]
    item = FoodItem(
        id="item-1",
        name="Rice noodles",
        quantity=180,
        unit="g",
        macros=Macros(protein=4, carbs=50, fat=1),
    )
    meal = Meal(
        meal_id="22222222-2222-4222-8222-222222222222",
        user_id="00000000-0000-0000-0000-000000000001",
        status=MealStatus.READY,
        image=MealImage(
            image_id="11111111-1111-4111-8111-111111111111",
            format="jpeg",
            size_bytes=100,
        ),
        dish_name="Rice noodle soup",
        nutrition=Nutrition(macros=item.macros, food_items=[item]),
        ready_at=datetime(2025, 1, 15),
        created_at=datetime(2025, 1, 15),
    )
    structured_data = {
        "dish_name": "Rice noodle soup",
        "localized_language": language,
        "localized_dish_name": localized_dish,
        "foods": [
            {"name": "Rice noodles", "localized_name": localized_food},
        ],
    }

    localization = parse_meal_response_localization(
        structured_data,
        f"{language}-地域",
        expected_food_count=1,
    )
    localized_meal = persist_meal_response_localization(meal, localization)

    assert localized_meal.dish_name == localized_dish
    assert localized_meal.nutrition.food_items[0].name == localized_food
    assert localized_meal.nutrition.food_items[0].macros == item.macros
    assert localized_meal.nutrition.food_items[0].quantity == item.quantity


@pytest.mark.parametrize(
    "mutator",
    [
        lambda data: data.pop("localized_language"),
        lambda data: data.update({"localized_language": "es"}),
        lambda data: data["foods"][0].pop("localized_name"),
    ],
)
def test_rejects_incomplete_or_wrong_locale(mutator):
    data = _structured_data()
    mutator(data)

    with pytest.raises(ValueError):
        parse_meal_response_localization(data, "vi", expected_food_count=1)
