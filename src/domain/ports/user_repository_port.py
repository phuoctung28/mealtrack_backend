"""
This module defines the abstract port for the user repository, ensuring a clean
separation between the domain and infrastructure layers.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from src.domain.model.user import UserDomainModel, UserProfileDomainModel


class UserRepositoryPort(ABC):
    """
    Interface for user repository operations.
    This port works exclusively with domain models.
    """

    @abstractmethod
    def save(self, user: UserDomainModel) -> UserDomainModel:
        """Save or update a user."""
        pass

    @abstractmethod
    def find_by_id(self, user_id: UUID) -> Optional[UserDomainModel]:
        """Find a user by ID."""
        pass

    @abstractmethod
    def find_by_firebase_uid(self, firebase_uid: str) -> Optional[UserDomainModel]:
        """Find a user by Firebase UID (active users only)."""
        pass

    @abstractmethod
    def find_deleted_by_firebase_uid(self, firebase_uid: str) -> Optional[UserDomainModel]:
        """Find a deleted user by Firebase UID (inactive users only)."""
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[UserDomainModel]:
        """Find a user by email."""
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> List[UserDomainModel]:
        """Find all users with pagination."""
        pass

    @abstractmethod
    def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID."""
        pass

    @abstractmethod
    def get_profile(self, user_id: UUID) -> Optional[UserProfileDomainModel]:
        """Get user profile by user ID."""
        pass

    @abstractmethod
    def update_profile(self, profile: UserProfileDomainModel) -> UserProfileDomainModel:
        """Update user profile."""
        pass