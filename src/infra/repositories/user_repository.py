"""Repository for user-related database operations."""
from typing import Optional, List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, email: str, username: str, password_hash: str, firebase_uid: str) -> User:
        """Create a new user."""
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            firebase_uid=firebase_uid,
            is_active=True
        )
        self.db.add(user)
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise ValueError("User with this email or username already exists")
    
    def get(self, user_id: str) -> Optional[User]:
        """Get user by ID (alias for compatibility)."""
        return self.get_user_by_id(user_id)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID."""
        return self.db.query(User).filter(User.firebase_uid == firebase_uid).first()
    
    def create_user_profile(self, user_id: str, age: int, gender: str, 
                          height_cm: float, weight_kg: float, 
                          body_fat_percentage: Optional[float] = None,
                          activity_level: str = 'sedentary',
                          fitness_goal: str = 'maintenance',
                          target_weight_kg: Optional[float] = None,
                          meals_per_day: int = 3,
                          snacks_per_day: int = 1,
                          dietary_preferences: List[str] = None,
                          health_conditions: List[str] = None,
                          allergies: List[str] = None) -> UserProfile:
        """Create a new user profile. Marks previous profiles as not current."""
        # Mark all existing profiles as not current
        self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id,
            UserProfile.is_current ==  True
        ).update({"is_current": False}, synchronize_session='evaluate')
        self.db.flush()
        
        profile = UserProfile(
            user_id=user_id,
            age=age,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            body_fat_percentage=body_fat_percentage,
            is_current=True,
            # Goal fields
            activity_level=activity_level,
            fitness_goal=fitness_goal,
            target_weight_kg=target_weight_kg,
            meals_per_day=meals_per_day,
            snacks_per_day=snacks_per_day,
            # Preference fields
            dietary_preferences=dietary_preferences or [],
            health_conditions=health_conditions or [],
            allergies=allergies or []
        )
        self.db.add(profile)
        self.db.commit()  # This will commit both the old profile updates and new profile creation
        self.db.refresh(profile)
        return profile
    
    def get_current_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get the current user profile."""
        return self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id,
            UserProfile.is_current == True
        ).first()
    
    def update_user_preferences(self, user_id: str, dietary_preferences: List[str] = None,
                              health_conditions: List[str] = None, allergies: List[str] = None) -> Optional[UserProfile]:
        """Update user preferences in their current profile."""
        profile = self.get_current_user_profile(user_id)
        if not profile:
            return None
            
        if dietary_preferences is not None:
            profile.dietary_preferences = dietary_preferences
        if health_conditions is not None:
            profile.health_conditions = health_conditions
        if allergies is not None:
            profile.allergies = allergies
            
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def update_user_goals(self, user_id: str, activity_level: str = None, fitness_goal: str = None,
                         target_weight_kg: Optional[float] = None, meals_per_day: int = None,
                         snacks_per_day: int = None) -> Optional[UserProfile]:
        """Update user goals in their current profile."""
        profile = self.get_current_user_profile(user_id)
        if not profile:
            return None
            
        if activity_level is not None:
            profile.activity_level = activity_level
        if fitness_goal is not None:
            profile.fitness_goal = fitness_goal
        if target_weight_kg is not None:
            profile.target_weight_kg = target_weight_kg
        if meals_per_day is not None:
            profile.meals_per_day = meals_per_day
        if snacks_per_day is not None:
            profile.snacks_per_day = snacks_per_day
            
        self.db.commit()
        self.db.refresh(profile)
        return profile