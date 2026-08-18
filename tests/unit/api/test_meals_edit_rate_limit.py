from src.api.routes.v1 import meals_edit


def test_meal_ingredient_writes_use_a_backstop_limit():
    assert meals_edit.MEAL_INGREDIENTS_EDIT_LIMIT == "60/minute"
    assert getattr(meals_edit.update_meal_ingredients, "__wrapped__", None) is not None
