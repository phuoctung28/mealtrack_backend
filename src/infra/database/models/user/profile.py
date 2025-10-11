"""
User profile model for physical attributes and personal information.
"""
from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey, Index, CheckConstraint, JSON
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
    is_current = Column(Boolean, default=True, nullable=False)
    
    # Goal fields (from UserGoal)
    activity_level = Column(String(30), nullable=False, default='sedentary')  # sedentary, light, moderate, active, extra
    fitness_goal = Column(String(30), nullable=False, default='maintenance')  # maintenance, cutting, bulking
    target_weight_kg = Column(Float, nullable=True)
    meals_per_day = Column(Integer, default=3, nullable=False)
    snacks_per_day = Column(Integer, default=1, nullable=False)
    
    # Preference fields (from UserPreferences)
    dietary_preferences = Column(JSON, default=[], nullable=False)  # ['vegan', 'vegetarian', 'gluten_free', etc.]
    health_conditions = Column(JSON, default=[], nullable=False)    # ['diabetes', 'hypertension', etc.]
    allergies = Column(JSON, default=[], nullable=False)           # ['nuts', 'dairy', 'shellfish', etc.]
    
    # Notification preferences
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    push_notifications_enabled = Column(Boolean, default=True, nullable=False)
    email_notifications_enabled = Column(Boolean, default=False, nullable=False)
    weekly_weight_reminder_enabled = Column(Boolean, default=False, nullable=False)
    weekly_weight_reminder_day = Column(Integer, default=0, nullable=False)  # 0=Sunday, 6=Saturday
    weekly_weight_reminder_time = Column(String(5), default='09:00', nullable=False)  # HH:mm format
    
    # Constraints
    __table_args__ = (
        CheckConstraint('age >= 13 AND age <= 120', name='check_age_range'),
        CheckConstraint('height_cm > 0', name='check_height_positive'),
        CheckConstraint('weight_kg > 0', name='check_weight_positive'),
        CheckConstraint('body_fat_percentage IS NULL OR (body_fat_percentage >= 0 AND body_fat_percentage <= 100)', 
                       name='check_body_fat_range'),
        CheckConstraint('weekly_weight_reminder_day >= 0 AND weekly_weight_reminder_day <= 6',
                       name='check_reminder_day_range'),
        Index('idx_user_current', 'user_id', 'is_current'),
    )
    
    # Relationships
    user = relationship("User", back_populates="profiles")