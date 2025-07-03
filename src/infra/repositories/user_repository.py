"""Repository for user-related database operations."""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.infra.database.models.user import (
    User, UserProfile, UserPreference, UserDietaryPreference,
    UserHealthCondition, UserAllergy, UserGoal
)
from src.infra.database.models.tdee_calculation import TdeeCalculation
from src.domain.model.macro_targets import SimpleMacroTargets


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, email: str, username: str, password_hash: str) -> User:
        """Create a new user."""
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
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
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def create_user_profile(self, user_id: str, age: int, gender: str, 
                          height_cm: float, weight_kg: float, 
                          body_fat_percentage: Optional[float] = None) -> UserProfile:
        """Create a new user profile. Marks previous profiles as not current."""
        # Mark all existing profiles as not current
        self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id,
            UserProfile.is_current == True
        ).update({"is_current": False})
        
        profile = UserProfile(
            user_id=user_id,
            age=age,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            body_fat_percentage=body_fat_percentage,
            is_current=True
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def get_current_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get the current user profile."""
        return self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id,
            UserProfile.is_current == True
        ).first()
    
    def create_user_preferences(self, user_id: str, dietary_preferences: List[str],
                              health_conditions: List[str], allergies: List[str]) -> UserPreference:
        """Create or update user preferences."""
        # Check if preferences already exist
        preference = self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()
        
        if not preference:
            preference = UserPreference(user_id=user_id)
            self.db.add(preference)
            self.db.flush()
        else:
            # Clear existing preferences
            self.db.query(UserDietaryPreference).filter(
                UserDietaryPreference.user_preference_id == preference.id
            ).delete()
            self.db.query(UserHealthCondition).filter(
                UserHealthCondition.user_preference_id == preference.id
            ).delete()
            self.db.query(UserAllergy).filter(
                UserAllergy.user_preference_id == preference.id
            ).delete()
        
        # Add dietary preferences
        for pref in dietary_preferences:
            dietary_pref = UserDietaryPreference(
                user_preference_id=preference.id,
                preference=pref
            )
            self.db.add(dietary_pref)
        
        # Add health conditions
        for condition in health_conditions:
            health_cond = UserHealthCondition(
                user_preference_id=preference.id,
                condition=condition
            )
            self.db.add(health_cond)
        
        # Add allergies
        for allergen in allergies:
            allergy = UserAllergy(
                user_preference_id=preference.id,
                allergen=allergen
            )
            self.db.add(allergy)
        
        self.db.commit()
        self.db.refresh(preference)
        return preference
    
    def get_user_preferences(self, user_id: str) -> Optional[UserPreference]:
        """Get user preferences."""
        return self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()
    
    def create_user_goal(self, user_id: str, activity_level: str, fitness_goal: str,
                        target_weight_kg: Optional[float] = None,
                        meals_per_day: int = 3, snacks_per_day: int = 1) -> UserGoal:
        """Create a new user goal. Marks previous goals as not current."""
        # Mark all existing goals as not current
        self.db.query(UserGoal).filter(
            UserGoal.user_id == user_id,
            UserGoal.is_current == True
        ).update({"is_current": False})
        
        goal = UserGoal(
            user_id=user_id,
            activity_level=activity_level,
            fitness_goal=fitness_goal,
            target_weight_kg=target_weight_kg,
            meals_per_day=meals_per_day,
            snacks_per_day=snacks_per_day,
            is_current=True
        )
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal
    
    def get_current_user_goal(self, user_id: str) -> Optional[UserGoal]:
        """Get the current user goal."""
        return self.db.query(UserGoal).filter(
            UserGoal.user_id == user_id,
            UserGoal.is_current == True
        ).first()
    
    def save_tdee_calculation(self, user_id: str, user_profile_id: str, user_goal_id: str,
                            bmr: float, tdee: float, target_calories: float,
                            macros: SimpleMacroTargets) -> TdeeCalculation:
        """Save a TDEE calculation."""
        calculation = TdeeCalculation(
            user_id=user_id,
            user_profile_id=user_profile_id,
            user_goal_id=user_goal_id,
            bmr=bmr,
            tdee=tdee,
            target_calories=target_calories,
            protein_grams=macros.protein,
            carbs_grams=macros.carbs,
            fat_grams=macros.fat
        )
        self.db.add(calculation)
        self.db.commit()
        self.db.refresh(calculation)
        return calculation
    
    def get_latest_tdee_calculation(self, user_id: str) -> Optional[TdeeCalculation]:
        """Get the most recent TDEE calculation for a user."""
        return self.db.query(TdeeCalculation).filter(
            TdeeCalculation.user_id == user_id
        ).order_by(TdeeCalculation.calculation_date.desc()).first()
    
    def get_tdee_history(self, user_id: str, limit: int = 30) -> List[TdeeCalculation]:
        """Get TDEE calculation history for a user."""
        return self.db.query(TdeeCalculation).filter(
            TdeeCalculation.user_id == user_id
        ).order_by(TdeeCalculation.calculation_date.desc()).limit(limit).all()