import src.infra.database.models as model_registry
from src.infra.database.base import Base


def test_model_registry_imports_expected_tables() -> None:
    assert model_registry.MealImageCacheModel.__tablename__ == "meal_image_cache"
    assert (
        model_registry.PendingMealImageResolutionModel.__tablename__
        == "pending_meal_image_resolution"
    )

    expected_tables = {
        "users",
        "user_profiles",
        "user_profile_preferences",
        "meal",
        "mealimage",
        "nutrition",
        "food_item",
        "food_reference",
        "food_reference_serving_sizes",
        "food_reference_nutrients",
        "hydration_entries",
        "meal_instruction_steps",
        "meal_image_cache",
        "pending_meal_image_resolution",
        "notifications",
        "notification_preferences",
        "user_fcm_tokens",
        "saved_suggestions",
        "saved_suggestion_items",
        "saved_suggestion_steps",
        "weekly_macro_budgets",
        "cheat_days",
        "referral_codes",
        "referral_conversions",
        "referral_wallets",
        "payout_requests",
        "weight_entries",
        "movement_entries",
        "email_logs",
        "promo_codes",
        "promo_code_redemptions",
    }

    assert expected_tables <= set(Base.metadata.tables)
