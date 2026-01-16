"""
Factory for creating test users and profiles.
"""
from uuid import uuid4
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile


class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    def create_user(session: Session, **overrides) -> User:
        """
        Create a user with sensible defaults.
        
        Args:
            session: Database session
            **overrides: Override any default user attributes
            
        Returns:
            User: Created user instance
        """
        user_id = str(uuid4())
        defaults = {
            "id": user_id,
            "firebase_uid": f"test_firebase_{user_id[:8]}",
            "email": f"test_{user_id[:8]}@example.com",
            "username": f"testuser_{user_id[:8]}",
            "password_hash": "test_hash",
            "is_active": True,
            "onboarding_completed": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "timezone": "UTC",
        }
        defaults.update(overrides)
        
        user = User(**defaults)
        session.add(user)
        session.flush()
        session.commit()
        return user
    
    @staticmethod
    def create_user_with_profile(
        session: Session,
        **user_overrides
    ) -> Tuple[User, UserProfile]:
        """
        Create user with profile.
        
        Args:
            session: Database session
            **user_overrides: Override any default user attributes
            
        Returns:
            Tuple of (User, UserProfile)
        """
        user = UserFactory.create_user(session, **user_overrides)
        
        profile_defaults = {
            "user_id": user.id,
            "age": 30,
            "gender": "male",
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity_level": "moderate",
            "fitness_goal": "recomp",
            "is_current": True,
            "meals_per_day": 3,
            "snacks_per_day": 1,
            "dietary_preferences": [],
            "health_conditions": [],
            "allergies": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        profile = UserProfile(**profile_defaults)
        session.add(profile)
        session.flush()
        session.commit()
        
        return user, profile
