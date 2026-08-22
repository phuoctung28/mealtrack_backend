from src.app.services.parse_text_composition import (
    classify_parse_text_input,
    composition_retry_feedback,
)


def test_named_dish_is_classified_for_composition():
    assert classify_parse_text_input("Bánh mì thịt") == "dish"
    assert classify_parse_text_input("1 bánh mì thịt") == "dish"
    assert classify_parse_text_input("1 bowl pho") == "dish"
    assert classify_parse_text_input("cơm tấm") == "dish"


def test_listed_or_measured_foods_are_not_dishes():
    assert classify_parse_text_input("trứng, sữa, bánh mì") == "ingredient_list"
    assert classify_parse_text_input("100g chicken breast") == "single_food"
    assert classify_parse_text_input("1 banana") == "single_food"
    assert classify_parse_text_input("thịt nướng") == "single_food"
    assert classify_parse_text_input("1 miếng sườn nướng") == "single_food"
    assert classify_parse_text_input("bánh flan") == "single_food"


def test_retry_feedback_only_when_a_dish_comes_back_as_one_row():
    assert composition_retry_feedback(
        "Bánh mì thịt",
        [{"name": "Pork sandwich", "lookup_name": "Vietnamese pork sandwich"}],
    )
    assert (
        composition_retry_feedback(
            "trứng, sữa",
            [{"name": "Trứng", "lookup_name": "Egg"}],
        )
        is None
    )
    assert (
        composition_retry_feedback(
            "Bánh mì thịt",
            [
                {"name": "Bánh mì", "lookup_name": "Baguette"},
                {"name": "Thịt", "lookup_name": "Pork"},
            ],
        )
        is None
    )
    assert (
        composition_retry_feedback(
            "100g chicken breast",
            [{"name": "Chicken breast", "lookup_name": "chicken breast"}],
        )
        is None
    )
