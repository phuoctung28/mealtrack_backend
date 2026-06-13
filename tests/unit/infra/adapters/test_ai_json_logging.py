"""Regression tests for AI JSON parser log redaction."""

import pytest

from src.app.handlers.command_handlers.meal_text_parsing_utils import (
    extract_json_from_response,
)
from src.infra.adapters.ai_json_utils import extract_json


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
