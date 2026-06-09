"""Meal suggestion domain exception classes."""


class MealSuggestionSessionStoreUnavailableError(RuntimeError):
    """Raised when transient suggestion session state cannot be persisted."""

    DEFAULT_MESSAGE = (
        "Redis suggestion session store write failed. "
        "Meal suggestion sessions require Redis until moved to durable storage."
    )

    def __init__(self, message: str = DEFAULT_MESSAGE) -> None:
        super().__init__(message)
