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
