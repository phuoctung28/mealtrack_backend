"""Validation helpers for structured AI output contracts."""

from typing import Any

from pydantic import BaseModel, ValidationError

from src.domain.exceptions.ai_exceptions import AIOutputValidationError

MAX_VALIDATION_DETAILS = 5
MAX_VALIDATION_DETAIL_CHARS = 120


def validate_ai_output(
    payload: Any,
    *,
    schema: type[BaseModel],
    purpose: str,
    attempt_count: int,
) -> dict[str, Any]:
    """Validate AI payload against a Pydantic contract and return a clean dump."""
    try:
        model = schema.model_validate(payload)
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIOutputValidationError(
            "Invalid AI structured output",
            purpose=purpose,
            attempt_count=attempt_count,
            validation_details=summarize_validation_error(exc),
        ) from exc
    return model.model_dump()


def summarize_validation_error(exc: Exception) -> list[str]:
    """Return compact, payload-free validation details for logs and retry prompts."""
    if isinstance(exc, ValidationError):
        details = []
        for error in exc.errors()[:MAX_VALIDATION_DETAILS]:
            location = _format_location(error.get("loc", ()))
            message = _sanitize_detail(str(error.get("msg", "invalid value")))
            details.append(f"{location}: {message}" if location else message)
        return details or ["invalid structured output"]

    detail = _sanitize_detail(str(exc))
    return [detail or "invalid structured output"]


def build_validation_retry_prompt(
    base_prompt: str, error: AIOutputValidationError
) -> str:
    """Append field-specific correction context without raw payload data."""
    details = "\n".join(f"- {detail}" for detail in error.validation_details)
    if not details:
        details = "- structured output did not match the required schema"

    return (
        f"{base_prompt}\n\n"
        "Your previous structured response did not match the required schema.\n"
        "Fix these validation issues:\n"
        f"{details}\n"
        "Return the full corrected response as valid JSON only."
    )


def _format_location(location: Any) -> str:
    if not isinstance(location, (tuple, list)):
        return str(location)
    return ".".join(str(part) for part in location)


def _sanitize_detail(detail: str) -> str:
    sanitized = " ".join(detail.split())
    if "input_value=" in sanitized:
        sanitized = sanitized.split("input_value=", 1)[0].rstrip(" ,")
    if len(sanitized) > MAX_VALIDATION_DETAIL_CHARS:
        sanitized = f"{sanitized[:MAX_VALIDATION_DETAIL_CHARS].rstrip()}..."
    return sanitized
