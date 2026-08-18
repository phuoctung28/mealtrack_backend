from src.app.services.food_display_name import (
    apply_fail_closed_display_names,
    leftover_display_names,
    needs_display_localization,
)


def test_leftover_display_names_collects_english_slash_segments():
    leftovers = leftover_display_names(
        [
            {"name": "Vietnamese Baguette"},
            {"name": "Bơ/mayo"},
            {"name": "Thịt"},
        ],
        "vi",
    )
    assert leftovers == ["Vietnamese Baguette", "mayo"]


def test_fail_closed_replaces_english_and_mixed_slash_names():
    items = [
        {"name": "Cilantro"},
        {"name": "Pork Pâté"},
        {"name": "Bơ/mayo"},
        {"name": "Whey Isolate"},
        {"name": "Thịt"},
    ]

    apply_fail_closed_display_names(items, "vi")

    assert [item["name"] for item in items] == [
        "Rau mùi",
        "Pate heo",
        "Bơ/Sốt mayonnaise",
        "Nguyên liệu",
        "Thịt",
    ]
    assert not any(needs_display_localization(item["name"], "vi") for item in items)
