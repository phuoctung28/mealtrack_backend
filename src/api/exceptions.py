"""
API Exception classes for consistent error handling.
"""


class ValidationException(MealTrackException):
    """Raised when request validation fails."""
    pass

class ResourceNotFoundException(MealTrackException):
    """Raised when a requested resource is not found."""
    pass

