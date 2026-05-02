"""Cover handle_exception generic Exception branch (unexpected errors)."""

from fastapi import HTTPException, status

from src.api.exceptions import handle_exception


def test_handle_exception_unexpected_returns_500():
    exc = handle_exception(RuntimeError("boom"))
    assert isinstance(exc, HTTPException)
    assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.detail["error_code"] == "INTERNAL_ERROR"
    assert "boom" in exc.detail["details"]["error"]
