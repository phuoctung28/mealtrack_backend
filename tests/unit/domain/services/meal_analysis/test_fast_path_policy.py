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
        MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=True,
        MEAL_ANALYZE_CANARY_PERCENT=35,
        MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED=False,
    )

    policy = MealAnalyzeFastPathPolicy.from_settings(settings)

    assert policy.primary_timeout_seconds == 3.75
    assert policy.retry_timeout_seconds == 2.25
    assert policy.max_attempts == 4
    assert policy.max_output_tokens == 900
    assert policy.translation_in_critical_path is True
    assert policy.runtime_policy_enabled is True
    assert policy.canary_percent == 35


def test_from_settings_reads_parallel_upload_flag():
    settings = SimpleNamespace(
        MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS=3.75,
        MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS=2.25,
        MEAL_ANALYZE_MAX_ATTEMPTS=4,
        MEAL_ANALYZE_MAX_OUTPUT_TOKENS=900,
        MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH=True,
        MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=True,
        MEAL_ANALYZE_CANARY_PERCENT=35,
        MEAL_ANALYZE_PARALLEL_UPLOAD_ENABLED=True,
    )

    policy = MealAnalyzeFastPathPolicy.from_settings(settings)

    assert policy.parallel_upload_enabled is True


def test_from_settings_uses_legacy_policy_when_runtime_policy_disabled():
    settings = SimpleNamespace(
        MEAL_ANALYZE_PRIMARY_TIMEOUT_SECONDS=3.75,
        MEAL_ANALYZE_RETRY_TIMEOUT_SECONDS=2.25,
        MEAL_ANALYZE_MAX_ATTEMPTS=4,
        MEAL_ANALYZE_MAX_OUTPUT_TOKENS=900,
        MEAL_ANALYZE_TRANSLATION_IN_CRITICAL_PATH=False,
        MEAL_ANALYZE_RUNTIME_POLICY_ENABLED=False,
        MEAL_ANALYZE_CANARY_PERCENT=100,
    )

    policy = MealAnalyzeFastPathPolicy.from_settings(settings)

    assert policy.runtime_policy_enabled is False
    assert policy.max_attempts == 1
    assert policy.translation_in_critical_path is True


def test_should_use_fast_path_obeys_canary_bounds():
    policy = MealAnalyzeFastPathPolicy(
        runtime_policy_enabled=True,
        canary_percent=0,
    )
    assert policy.should_use_fast_path("any-user") is False

    full_policy = MealAnalyzeFastPathPolicy(
        runtime_policy_enabled=True,
        canary_percent=100,
    )
    assert full_policy.should_use_fast_path("any-user") is True
