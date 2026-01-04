"""Repository for user-related database operations."""
import json
import logging
from typing import Optional, List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User

logger = logging.getLogger(__name__)


_USER_RELATIONSHIP_LOADS = (
    selectinload(User.profiles),
    selectinload(User.subscriptions),
)


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save(self, user: User) -> User:
        """Save or update a user."""
        if not user.id:
            self.db.add(user)
        else:
            self.db.merge(user)
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise ValueError("User with this email or username already exists")
    
    def create_user(self, email: str, username: str, password_hash: str, firebase_uid: str) -> User:
        """Create a new user (deprecated - use save instead)."""
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            firebase_uid=firebase_uid,
            is_active=True
        )
        return self.save(user)
    
    def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID (only active users)."""
        return (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(
                User.id == user_id,
                User.is_active == True
            )
            .first()
        )
    
    def get(self, user_id: str) -> Optional[User]:
        """Get user by ID (deprecated - use find_by_id)."""
        return self.find_by_id(user_id)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (deprecated - use find_by_id)."""
        return self.find_by_id(user_id)

    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email (only active users)."""
        return (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(
                User.email == email,
                User.is_active == True
            )
            .first()
        )
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (deprecated - use find_by_email)."""
        return self.find_by_email(email)

    def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username (only active users)."""
        return (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(
                User.username == username,
                User.is_active == True
            )
            .first()
        )
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (deprecated - use find_by_username)."""
        return self.find_by_username(username)

    def find_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Find user by Firebase UID (only active users)."""
        return (
            self.db.query(User)
            .options(*_USER_RELATIONSHIP_LOADS)
            .filter(
                User.firebase_uid == firebase_uid,
                User.is_active == True
            )
            .first()
        )
    
    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID (deprecated - use find_by_firebase_uid)."""
        return self.find_by_firebase_uid(firebase_uid)
    
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

    async def get_current_profile_cached(
        self,
        user_id: str,
        redis_client=None
    ) -> Optional[UserProfile]:
        """
        Get current profile with 1-hour Redis cache.
        Optimized for meal suggestion generation.
        """
        # Try cache first
        if redis_client:
            cache_key = f"user_profile_current:{user_id}"
            try:
                cached_data = await redis_client.get(cache_key)

                if cached_data:
                    data = json.loads(cached_data)
                    # Reconstruct profile object
                    profile = UserProfile()
                    profile.id = data["id"]
                    profile.user_id = data["user_id"]
                    profile.age = data["age"]
                    profile.gender = data["gender"]
                    profile.height_cm = data["height_cm"]
                    profile.weight_kg = data["weight_kg"]
                    profile.body_fat_percentage = data.get("body_fat_percentage")
                    profile.activity_level = data["activity_level"]
                    profile.fitness_goal = data["fitness_goal"]
                    profile.meals_per_day = data["meals_per_day"]
                    profile.dietary_preferences = data.get("dietary_preferences", [])
                    profile.allergies = data.get("allergies", [])
                    logger.debug(f"Cache hit for user profile {user_id}")
                    return profile
            except Exception as e:
                logger.warning(f"Failed to read profile from cache: {e}")

        # Cache miss - query DB (optimized, no relationships)
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id,
            UserProfile.is_current == True
        ).first()

        # Cache for 1 hour
        if profile and redis_client:
            try:
                cache_data = json.dumps({
                    "id": profile.id,
                    "user_id": profile.user_id,
                    "age": profile.age,
                    "gender": profile.gender,
                    "height_cm": profile.height_cm,
                    "weight_kg": profile.weight_kg,
                    "body_fat_percentage": profile.body_fat_percentage,
                    "activity_level": profile.activity_level,
                    "fitness_goal": profile.fitness_goal,
                    "meals_per_day": profile.meals_per_day,
                    "dietary_preferences": profile.dietary_preferences or [],
                    "allergies": profile.allergies or []
                })
                await redis_client.set(cache_key, cache_data, ttl=3600)  # 1 hour TTL
                logger.debug(f"Cached user profile {user_id}")
            except Exception as e:
                logger.warning(f"Failed to cache profile: {e}")

        return profile

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
    
    def update_user_timezone(self, user_id: str, timezone: str) -> bool:
        """Update user's timezone."""
        try:
            user = self.find_by_id(user_id)
            if user:
                user.timezone = timezone
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating timezone for user {user_id}: {e}")
            raise e