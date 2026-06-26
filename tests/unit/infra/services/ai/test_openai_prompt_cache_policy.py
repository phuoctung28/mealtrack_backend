import pytest

from src.infra.services.ai.openai_prompt_cache_policy import (
    OpenAIPromptCachePolicy,
)


def test_disabled_policy_returns_empty_kwargs():
    policy = OpenAIPromptCachePolicy(enabled=False)

    result = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )

    assert result == {}


def test_enabled_policy_returns_stable_key_for_same_system_prompt():
    policy = OpenAIPromptCachePolicy(enabled=True, key_prefix="mealtrack")

    first = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )
    second = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )

    assert first == second
    assert first["prompt_cache_key"].startswith("mealtrack:meal_scan:")


def test_key_changes_when_model_or_system_prompt_changes():
    policy = OpenAIPromptCachePolicy(enabled=True, key_prefix="mealtrack")

    base = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )
    other_model = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-18",
        purpose_hint="meal_scan",
        system_message="Return canonical meal JSON.",
    )
    other_system = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="meal_scan",
        system_message="Return canonical ingredient JSON.",
    )

    assert base["prompt_cache_key"] != other_model["prompt_cache_key"]
    assert base["prompt_cache_key"] != other_system["prompt_cache_key"]


def test_key_does_not_contain_raw_system_prompt():
    policy = OpenAIPromptCachePolicy(enabled=True, key_prefix="mealtrack")

    result = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="parse_text",
        system_message="secret patient meal instruction",
    )

    assert "secret" not in result["prompt_cache_key"]
    assert "patient" not in result["prompt_cache_key"]
    assert "instruction" not in result["prompt_cache_key"]


def test_retention_is_added_when_configured():
    policy = OpenAIPromptCachePolicy(
        enabled=True,
        key_prefix="mealtrack",
        retention="24h",
    )

    result = policy.request_kwargs(
        model="gpt-5.4-mini-2026-03-17",
        purpose_hint="recipe",
        system_message="Return recipe JSON.",
    )

    assert result["prompt_cache_retention"] == "24h"


def test_invalid_retention_raises_value_error():
    with pytest.raises(ValueError, match="OPENAI_PROMPT_CACHE_RETENTION"):
        OpenAIPromptCachePolicy(enabled=True, retention="forever")
