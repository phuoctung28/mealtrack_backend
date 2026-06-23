"""Regression tests for AI JSON parser log redaction and observability metrics."""

from unittest.mock import patch

import pytest

from src.app.handlers.command_handlers.meal_text_parsing_utils import (
    extract_json_from_response,
)
from src.infra.adapters.ai_json_utils import extract_json
from src.observability_connectors import SAFE_CONTEXT_KEYS, SAFE_TAG_KEYS


def test_shared_ai_json_extractor_does_not_log_raw_response(caplog):
    raw_response = "broken json with private meal notes and user@example.com"

    with caplog.at_level("ERROR"), pytest.raises(ValueError):
        extract_json(raw_response)

    assert raw_response not in caplog.text
    assert "user@example.com" not in caplog.text
    assert "content_len=" in caplog.text


def test_meal_text_json_extractor_does_not_log_raw_response(caplog):
    raw_response = "not an array with private meal notes and user@example.com"

    with caplog.at_level("ERROR"), pytest.raises(ValueError):
        extract_json_from_response(raw_response)

    assert raw_response not in caplog.text
    assert "user@example.com" not in caplog.text
    assert "length=" in caplog.text


# ---------------------------------------------------------------------------
# Observability allowlist tests
# ---------------------------------------------------------------------------


def test_ai_safe_context_keys_include_ai_fields():
    """AI observability keys must be in SAFE_CONTEXT_KEYS so they pass the filter."""
    required = {"ai_provider", "ai_model", "ai_purpose", "failure_kind"}
    assert required <= SAFE_CONTEXT_KEYS, (
        f"Missing from SAFE_CONTEXT_KEYS: {required - SAFE_CONTEXT_KEYS}"
    )


def test_ai_safe_tag_keys_include_ai_fields():
    """AI observability keys must be in SAFE_TAG_KEYS so they can be used as provider tags."""
    required = {"ai_provider", "ai_model", "ai_purpose", "failure_kind"}
    assert required <= SAFE_TAG_KEYS, (
        f"Missing from SAFE_TAG_KEYS: {required - SAFE_TAG_KEYS}"
    )


def test_parse_failure_emits_metric():
    """extract_json() must emit ai.vision.parse_failure.count when all parse attempts fail."""
    invalid_content = "this is not json at all !!!"

    with patch("src.observability.increment_metric") as mock_metric:
        with pytest.raises(ValueError):
            extract_json(invalid_content)

    emitted_names = [call.args[0] for call in mock_metric.call_args_list]
    assert "ai.vision.parse_failure.count" in emitted_names, (
        f"Expected 'ai.vision.parse_failure.count' in emitted metrics, got: {emitted_names}"
    )
