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


class MealRecommendationNotFoundError(MealRecommendationCreationError):
    """Raised when an owner-scoped plan or slot is not found."""

    public_detail = "Meal recommendation not found"
    status_code = 404


class MealRecommendationVersionConflictError(MealRecommendationCreationError):
    """Raised when a slot version precondition fails."""

    public_detail = "Meal recommendation slot has changed"
    status_code = 409


class MealRecommendationInvalidAlternativeError(MealRecommendationCreationError):
    """Raised when a requested swap target is not valid for the slot."""

    public_detail = "Meal recommendation alternative is not valid"
    status_code = 422


class MealRecommendationAlreadyLoggedError(MealRecommendationCreationError):
    """Raised when a slot has already been logged as a meal."""

    public_detail = "Meal recommendation slot is already logged"
    status_code = 409


class MealRecommendationNotLoggedError(MealRecommendationCreationError):
    """Raised when relog is requested before the slot has been logged."""

    public_detail = "Meal recommendation slot has not been logged yet"
    status_code = 409


class MealRecommendationTerminalStateError(MealRecommendationCreationError):
    """Raised when a terminal slot outcome already exists."""

    public_detail = "Meal recommendation slot already has a terminal outcome"
    status_code = 409
