"""Repository for user-related database operations."""
import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from src.domain.model.user import UserDomainModel, UserProfileDomainModel
from src.domain.ports.user_repository_port import UserRepositoryPort
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User
from src.infra.mappers.user_mapper import UserMapper, UserProfileMapper

logger = logging.getLogger(__name__)


_USER_RELATIONSHIP_LOADS = (
    selectinload(User.profiles),
    selectinload(User.subscriptions),
)


class UserRepository(UserRepositoryPort):
    """
    SQLAlchemy implementation of the user repository.
    This class adapts the database models to the domain models.
    """

    def __init__(self, db: Session):
        self.db = db

    def save(self, user_domain: UserDomainModel) -> UserDomainModel:
        """Save or update a user."""
        user_entity = UserMapper.to_persistence(user_domain)
        # Manually set profiles as they are a relationship
        user_entity.profiles = [UserProfileMapper.to_persistence(p) for p in user_domain.profiles]

        if not user_entity.id:
            self.db.add(user_entity)
        else:
            user_entity = self.db.merge(user_entity)
        try:
            self.db.commit()
            self.db.refresh(user_entity)
            return UserMapper.to_domain(user_entity)
        except IntegrityError:
            self.db.rollback()
            raise ValueError("User with this email or username already exists")

    def find_by_id(self, user_id: UUID) -> Optional[UserDomainModel]:
        """Find user by ID (only active users)."""
        # Convert UUID to string for comparison since User.id is String(36)
        # SQLAlchemy should handle this automatically, but SQLite may need explicit conversion
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        user_entity = (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(User.id == user_id_str, User.is_active == True)
            .first()
        )
        return UserMapper.to_domain(user_entity) if user_entity else None

    def find_by_email(self, email: str) -> Optional[UserDomainModel]:
        """Find user by email (only active users)."""
        user_entity = (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(User.email == email, User.is_active == True)
            .first()
        )
        return UserMapper.to_domain(user_entity) if user_entity else None

    def find_by_firebase_uid(self, firebase_uid: str) -> Optional[UserDomainModel]:
        """Find user by Firebase UID (only active users)."""
        user_entity = (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(User.firebase_uid == firebase_uid, User.is_active == True)
            .first()
        )
        return UserMapper.to_domain(user_entity) if user_entity else None

    def find_all(self, limit: int = 100, offset: int = 0) -> List[UserDomainModel]:
        """Find all users with pagination."""
        user_entities = (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(User.is_active == True)
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [UserMapper.to_domain(u) for u in user_entities]

    def delete(self, user_id: UUID) -> bool:
        """'Delete' a user by marking them as inactive."""
        # Convert UUID to string for SQLite compatibility
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        user_entity = self.db.query(User).filter(User.id == user_id_str).first()
        if user_entity:
            user_entity.is_active = False
            self.db.commit()
            return True
        return False

    def get_profile(self, user_id: UUID) -> Optional[UserProfileDomainModel]:
        """Get the current user profile."""
        # Convert UUID to string for SQLite compatibility
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        profile_entity = (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id_str, UserProfile.is_current == True)
            .first()
        )
        return UserProfileMapper.to_domain(profile_entity) if profile_entity else None

    def update_profile(self, profile_domain: UserProfileDomainModel) -> UserProfileDomainModel:
        """Update or create user profile (upsert)."""
        # Convert UUID to string for SQLite compatibility
        profile_id_str = str(profile_domain.id) if isinstance(profile_domain.id, UUID) else profile_domain.id
        profile_entity = self.db.query(UserProfile).get(profile_id_str)
        
        if not profile_entity:
            # Create new profile if it doesn't exist
            profile_entity = UserProfileMapper.to_persistence(profile_domain)
            self.db.add(profile_entity)
        else:
            # Update existing profile
            profile_data = profile_domain.__dict__
            for key, value in profile_data.items():
                if hasattr(profile_entity, key) and key != '_sa_instance_state':
                    setattr(profile_entity, key, value)

        self.db.commit()
        self.db.refresh(profile_entity)
        return UserProfileMapper.to_domain(profile_entity)
