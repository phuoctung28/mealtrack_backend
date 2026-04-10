"""
User profile model for physical attributes and personal information.
"""
from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey, Index, CheckConstraint, JSON, Date
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class UserProfile(Base, BaseMixin):
    """Stores user physical attributes and personal info with historical tracking."""
    __tablename__ = 'user_profiles'
    
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)  # male, female, other
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    body_fat_percentage = Column(Float, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    is_current = Column(Boolean, default=True, nullable=False)
    
    # Goal fields (from UserGoal)
    job_type = Column(String(30), nullable=False, default='desk')  # desk, on_feet, physical
    training_days_per_week = Column(Integer, nullable=False, default=0)  # 0-7
    training_minutes_per_session = Column(Integer, nullable=False, default=0)  # 15-180
    fitness_goal = Column(String(30), nullable=False, default='maintenance')  # maintenance, cutting, bulking
    target_weight_kg = Column(Float, nullable=True)
    meals_per_day = Column(Integer, default=3, nullable=False)
    snacks_per_day = Column(Integer, default=1, nullable=False)

    # Training experience level (beginner, intermediate, advanced)
    training_level = Column(String(20), nullable=True, default=None)

    # Onboarding redesign fields (NM-44)
    challenge_duration = Column(String(30), nullable=True, default=None)
    training_types = Column(JSON, nullable=True, default=None)

    # Custom macro overrides — when ALL three non-null, overrides calculated macros
    custom_protein_g = Column(Float, nullable=True, default=None)
    custom_carbs_g = Column(Float, nullable=True, default=None)
    custom_fat_g = Column(Float, nullable=True, default=None)

    @property
    def has_custom_macros(self) -> bool:
        """True when user has set custom macro overrides."""
        return (
            self.custom_protein_g is not None
            and self.custom_carbs_g is not None
            and self.custom_fat_g is not None
        )
    
    # Preference fields (from UserPreferences)
    dietary_preferences = Column(JSON, default=[], nullable=False)  # ['vegan', 'vegetarian', 'gluten_free', etc.]
    health_conditions = Column(JSON, default=[], nullable=False)    # ['diabetes', 'hypertension', etc.]
    allergies = Column(JSON, default=[], nullable=False)           # ['nuts', 'dairy', 'shellfish', etc.]
    pain_points = Column(JSON, default=[], nullable=True)
    disliked_foods = Column(JSON, nullable=True)  # soft exclusion for discovery (NM-63), [] in app code

    # Attribution — JSON array, nullable for existing users
    referral_sources = Column(JSON, nullable=True, default=None)

    # Constraints
    __table_args__ = (
        CheckConstraint('age >= 13 AND age <= 120', name='check_age_range'),
        CheckConstraint('height_cm > 0', name='check_height_positive'),
        CheckConstraint('weight_kg > 0', name='check_weight_positive'),
        CheckConstraint('body_fat_percentage IS NULL OR (body_fat_percentage >= 0 AND body_fat_percentage <= 100)', 
                       name='check_body_fat_range'),
        Index('idx_user_current', 'user_id', 'is_current'),
    )
    
    # Relationships
    user = relationship("User", back_populates="profiles")