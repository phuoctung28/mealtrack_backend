"""AI-related exception classes for resilience layer."""

from typing import Any, List, Optional


class AIError(Exception):
    """Base class for AI-related errors."""

    pass


class AIUnavailableError(AIError):
    """Raised when all AI models/providers are exhausted."""

    def __init__(
        self,
        message: str,
        attempted_models: Optional[List[str]] = None,
        last_error: Optional[str] = None,
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
        successful: Optional[List[Any]] = None,
        failed: Optional[List[Any]] = None,
    ) -> None:
        super().__init__(message)
        self.successful = successful or []
        self.failed = failed or []
