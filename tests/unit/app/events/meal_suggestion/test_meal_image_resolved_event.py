def test_meal_image_resolved_event_import():
    from src.app.events.meal_suggestion.meal_image_resolved_event import (
        MealImageResolvedEvent,
    )

    assert MealImageResolvedEvent is not None
