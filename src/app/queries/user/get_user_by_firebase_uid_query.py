"""
Query to get user by Firebase UID.
"""
from dataclasses import dataclass


@dataclass
class GetUserByFirebaseUidQuery:
    """Query to get user by Firebase UID."""
    firebase_uid: str
