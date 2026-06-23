"""AI-related exception classes for resilience layer."""

from enum import Enum
from typing import Any


class AIVisionFailureKind(Enum):
    """Classified failure reason for a vision provider call."""

    transient = "transient"
    timeout = "timeout"
    rate_limit = "rate_limit"
    schema_validation = "schema_validation"
    json_parse = "json_parse"
    no_food = "no_food"
    unknown = "unknown"


class AIVisionError(Exception):
    """Raised by vision providers with a classified failure kind.

    Schema/parse kinds must NOT trip the circuit breaker — they are deterministic
    failures that retrying on the same model cannot fix.
    """

    def __init__(
        self,
        message: str,
        kind: AIVisionFailureKind,
        provider: str = "",
        model: str = "",
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.provider = provider
        self.model = model


class AIError(Exception):
    """Base class for AI-related errors."""

    pass


class AIUnavailableError(AIError):
    """Raised when all AI models/providers are exhausted."""

    def __init__(
        self,
        message: str,
        attempted_models: list[str] | None = None,
        last_error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.attempted_models = attempted_models or []
        self.last_error = last_error

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.attempted_models:
            parts.append(f"attempted_models={self.attempted_models}")
        if self.last_error:
            parts.append(f"last_error={self.last_error}")
        return " | ".join(parts)


class AIPartialResultError(AIError):
    """Raised when batch operation has partial success."""

    def __init__(
        self,
        message: str,
        successful: list[Any] | None = None,
        failed: list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.successful = successful or []
        self.failed = failed or []


class AIOutputValidationError(AIError):
    """Raised when an AI response fails the expected structured output contract."""

    def __init__(
        self,
        message: str,
        *,
        purpose: str,
        attempt_count: int,
        validation_details: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.purpose = purpose
        self.attempt_count = attempt_count
        self.validation_details = validation_details or []

    def __str__(self) -> str:
        parts = [
            super().__str__(),
            f"purpose={self.purpose}",
            f"attempt_count={self.attempt_count}",
        ]
        if self.validation_details:
            parts.append(f"validation_details={self.validation_details}")
        return " | ".join(parts)
