"""Delete user account command."""
from dataclasses import dataclass


@dataclass
class DeleteUserCommand:
    """Command to delete a user account (soft delete in DB, hard delete in Firebase)."""

    firebase_uid: str
