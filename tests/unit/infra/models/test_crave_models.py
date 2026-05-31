from src.infra.database.models.crave.crave_seen_model import CraveSeen
from src.infra.database.models.crave.crave_swipe_event_model import CraveSwipeEvent
from src.infra.database.models.crave.meal_catalog_model import MealCatalog
from src.infra.database.models.crave.user_taste_profile_model import UserTasteProfile
from src.infra.database.models.saved_suggestion import SavedSuggestionModel


def test_meal_catalog_defaults_and_columns():
    meal = MealCatalog(
        id="cat_1",
        meal_name="Teriyaki Salmon Bowl",
        english_name="Teriyaki Salmon Bowl",
        calories=520,
        protein_g=42.0,
        carbs_g=48.0,
        fat_g=16.0,
        fiber_g=6.0,
        calorie_band=500,
        cuisine="japanese",
        meal_types=["lunch", "dinner"],
        ingredients=[{"name": "salmon", "grams": 150}],
        dietary_flags=["pescatarian"],
        allergen_flags=["fish"],
        tags=["high_protein"],
        recipe_status="none",
        origin="generated",
        status="active",
    )

    assert meal.recipe_steps is None
    assert meal.times_shown is None or meal.times_shown == 0
    assert meal.times_saved is None or meal.times_saved == 0
    assert meal.allergen_flags == ["fish"]
    assert meal.status == "active"


def test_taste_profile_defaults():
    profile = UserTasteProfile(user_id="user_1")

    assert profile.cuisine_affinity is None or profile.cuisine_affinity == {}
    assert profile.ingredient_affinity is None or profile.ingredient_affinity == {}
    assert profile.tag_affinity is None or profile.tag_affinity == {}
    assert profile.swipe_count is None or profile.swipe_count == 0
    assert profile.taste_embedding is None


def test_swipe_event_columns():
    event = CraveSwipeEvent(
        id="sw_1",
        user_id="user_1",
        catalog_meal_id="cat_1",
        deck_id="deck_1",
        direction="save",
        position=0,
        dwell_ms=1200,
        meal_type="lunch",
        context={"budget": 540},
    )

    assert event.direction == "save"
    assert event.position == 0


def test_crave_seen_columns():
    seen = CraveSeen(user_id="user_1", catalog_meal_id="cat_1", seen_count=1)

    assert seen.seen_count == 1


def test_saved_suggestion_has_crave_fields():
    saved = SavedSuggestionModel(
        id="s1",
        user_id="u1",
        suggestion_id="cat_1",
        meal_type="lunch",
        catalog_meal_id="cat_1",
        source="crave",
        suggestion_data={},
    )

    assert saved.catalog_meal_id == "cat_1"
    assert saved.source == "crave"
