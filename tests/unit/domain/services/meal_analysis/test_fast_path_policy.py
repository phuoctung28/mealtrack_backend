from types import SimpleNamespace

from src.domain.services.meal_analysis.fast_path_policy import (
    MealAnalyzeFastPathPolicy,
)


def test_defaults_from_settings_none():
    policy = MealAnalyzeFastPathPolicy.from_settings(None)

    assert policy.primary_timeout_seconds == 2.5
    assert policy.retry_timeout_seconds == 1.5
    assert policy.max_attempts == 2
    assert policy.max_output_tokens == 700
    assert policy.translation_in_critical_path is False


def test_from_settings_maps_values():
    settings = SimpleNamespace(
        MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS=3.75,
        MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS=2.25,
        MEAL_ANALYZE_MAX_ATTEMPTS=4,
        MEAL_ANALYZE_MAX_OUTPUT_TOKENS=900,
        MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH=True,
    )

    policy = MealAnalyzeFastPathPolicy.from_settings(settings)

    assert policy.primary_timeout_seconds == 3.75
    assert policy.retry_timeout_seconds == 2.25
    assert policy.max_attempts == 4
    assert policy.max_output_tokens == 900
    assert policy.translation_in_critical_path is True
