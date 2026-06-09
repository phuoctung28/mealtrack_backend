from datetime import UTC, datetime

from src.infra.database.models.saved_suggestion import SavedSuggestionModel
from src.infra.repositories.saved_suggestion_normalization import (
    apply_normalized_saved_suggestion_fields,
    saved_suggestion_model_to_dict,
)


def test_saved_suggestion_projection_prefers_normalized_rows() -> None:
    model = SavedSuggestionModel(
        id="saved-1",
        user_id="user-1",
        suggestion_id="suggestion-1",
        meal_type="lunch",
        portion_multiplier=1,
        suggestion_data={
            "dish_name": "Old name",
            "ingredients": ["legacy ingredient"],
            "instructions": ["legacy step"],
        },
        saved_at=datetime(2026, 6, 9, tzinfo=UTC),
        created_at=datetime(2026, 6, 9, tzinfo=UTC),
    )
    apply_normalized_saved_suggestion_fields(
        model,
        {
            "name": "Chicken rice",
            "macros": {"protein": 30, "carbs": 40, "fat": 10},
            "ingredients": [
                {"name": "Chicken", "amount": 150, "unit": "g", "protein": 30}
            ],
            "instructions": [{"instruction": "Grill chicken", "duration_minutes": 12}],
        },
    )

    result = saved_suggestion_model_to_dict(model)

    assert result["suggestion_data"]["dish_name"] == "Chicken rice"
    assert result["suggestion_data"]["macros"]["protein"] == 30.0
    assert result["suggestion_data"]["ingredients"][0]["name"] == "Chicken"
    assert (
        result["suggestion_data"]["instructions"][0]["instruction"] == "Grill chicken"
    )


def test_saved_suggestion_projection_tolerates_malformed_payload() -> None:
    model = SavedSuggestionModel(
        id="saved-1",
        user_id="user-1",
        suggestion_id="suggestion-1",
        meal_type="snack",
        portion_multiplier=1,
        suggestion_data={"ingredients": [None, {"amount": "bad"}], "steps": [None]},
        saved_at=None,
        created_at=datetime(2026, 6, 9, tzinfo=UTC),
    )
    apply_normalized_saved_suggestion_fields(model, model.suggestion_data)

    result = saved_suggestion_model_to_dict(model)

    assert result["suggestion_data"]["ingredients"] == [None, {"amount": "bad"}]
    assert result["suggestion_data"]["steps"] == [None]
