from types import SimpleNamespace

from src.domain.services.meal_analysis.fast_path_policy import (
    MealAnalyzeFastPathPolicy,
)


def test_defaults_from_settings_none():
    policy = MealAnalyzeFastPathPolicy.from_settings(None)

    assert policy.max_attempts == 2
    assert policy.max_output_tokens == 700


def test_from_settings_maps_values():
    settings = SimpleNamespace(
        MEAL_ANALYZE_MAX_ATTEMPTS=4,
        MEAL_ANALYZE_MAX_OUTPUT_TOKENS=900,
    )

    policy = MealAnalyzeFastPathPolicy.from_settings(settings)

    assert policy.max_attempts == 4
    assert policy.max_output_tokens == 900


def test_from_settings_uses_defaults_for_missing_attrs():
    settings = SimpleNamespace()

    policy = MealAnalyzeFastPathPolicy.from_settings(settings)

    assert policy.max_attempts == 2
    assert policy.max_output_tokens == 700
