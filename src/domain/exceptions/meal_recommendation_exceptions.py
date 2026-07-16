"""Exceptions for durable meal recommendations."""


class MealRecommendationCreationError(Exception):
    """Base error for durable meal recommendation creation failures."""

    public_detail = "Unable to create meal recommendations"
    status_code = 503

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_detail)


class MealRecommendationIdempotencyConflictError(MealRecommendationCreationError):
    """Raised when an idempotency key is reused for a different request."""

    public_detail = "Idempotency-Key was reused with a different request"
    status_code = 409


class MealRecommendationCatalogUnavailableError(MealRecommendationCreationError):
    """Raised when no usable catalog release is available."""

    public_detail = "Meal recommendation catalog is unavailable"
    status_code = 503


class MealRecommendationInsufficientCatalogError(MealRecommendationCreationError):
    """Raised when the active catalog cannot satisfy the requested plan."""

    public_detail = "Meal recommendation catalog cannot satisfy this request"
    status_code = 422


class MealRecommendationPersistenceConflictError(MealRecommendationCreationError):
    """Raised when durable write constraints race despite generation serialization."""

    public_detail = "Meal recommendation request is already being processed"
    status_code = 409
