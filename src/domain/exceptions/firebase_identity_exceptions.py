"""Exceptions for conflicts between Firebase and local account identities."""


class FirebaseIdentityConflictError(Exception):
    """Raised when a Firebase UID attempts to claim another account's email."""

