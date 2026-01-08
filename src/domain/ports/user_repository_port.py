"""
UserRepositoryPort - Interface for user repository operations.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    # Only import for type checking, not at runtime
    from src.infra.database.models.user import User, UserProfile


class UserRepositoryPort(ABC):
    """Interface for user repository operations."""
    
    @abstractmethod
    def save(self, user: "User") -> "User":
        """Save or update a user."""
        pass
    
    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional["User"]:
        """Find a user by ID."""
        pass
    
    @abstractmethod
    def find_by_firebase_uid(self, firebase_uid: str) -> Optional["User"]:
        """Find a user by Firebase UID."""
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional["User"]:
        """Find a user by email."""
        pass
    
    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> List["User"]:
        """Find all users with pagination."""
        pass
    
    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete a user by ID."""
        pass
    
    @abstractmethod
    def update_last_accessed(self, user_id: str, timestamp: datetime) -> bool:
        """Update user's last accessed timestamp."""
        pass
    
    @abstractmethod
    def get_profile(self, user_id: str) -> Optional["UserProfile"]:
        """Get user profile by user ID."""
        pass
    
    @abstractmethod
    def update_profile(self, user_id: str, profile: "UserProfile") -> "UserProfile":
        """Update user profile."""
        pass