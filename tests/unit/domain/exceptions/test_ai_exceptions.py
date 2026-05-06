import pytest
from src.domain.exceptions.ai_exceptions import (
    AIError,
    AIUnavailableError,
    AIPartialResultError,
)


def test_ai_error_is_base_exception():
    err = AIError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"


def test_ai_unavailable_error_inherits_from_ai_error():
    err = AIUnavailableError("all models failed")
    assert isinstance(err, AIError)
    assert str(err) == "all models failed"


def test_ai_unavailable_error_with_details():
    err = AIUnavailableError(
        "all models failed",
        attempted_models=["flash", "flash-lite"],
        last_error="503 UNAVAILABLE",
    )
    assert err.attempted_models == ["flash", "flash-lite"]
    assert err.last_error == "503 UNAVAILABLE"


def test_ai_partial_result_error_stores_results():
    successful = [{"name": "meal1"}, {"name": "meal2"}]
    failed = [{"index": 2, "error": "timeout"}]
    err = AIPartialResultError(
        "partial failure",
        successful=successful,
        failed=failed,
    )
    assert isinstance(err, AIError)
    assert err.successful == successful
    assert err.failed == failed
    assert len(err.successful) == 2
    assert len(err.failed) == 1


def test_ai_unavailable_error_default_values():
    err = AIUnavailableError("failed")
    assert err.attempted_models == []
    assert err.last_error is None


def test_ai_partial_result_error_default_values():
    err = AIPartialResultError("partial")
    assert err.successful == []
    assert err.failed == []
