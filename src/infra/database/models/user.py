from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class User(Base, BaseMixin):
    """Core user table for authentication and account management."""
    __tablename__ = 'users'
    
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    profiles = relationship("UserProfile", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals = relationship("UserGoal", back_populates="user", cascade="all, delete-orphan")
    tdee_calculations = relationship("TdeeCalculation", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def current_profile(self):
        """Get the current active profile."""
        return next((p for p in self.profiles if p.is_current), None)
    
    @property
    def current_goal(self):
        """Get the current active goal."""
        return next((g for g in self.goals if g.is_current), None)


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
    tdee_calculations = relationship("TdeeCalculation", back_populates="profile")


class UserPreference(Base, BaseMixin):
    """Stores user dietary preferences and health-related information."""
    __tablename__ = 'user_preferences'
    
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    dietary_preferences = relationship("UserDietaryPreference", back_populates="preference", cascade="all, delete-orphan")
    health_conditions = relationship("UserHealthCondition", back_populates="preference", cascade="all, delete-orphan")
    allergies = relationship("UserAllergy", back_populates="preference", cascade="all, delete-orphan")


class UserDietaryPreference(Base, BaseMixin):
    """Dietary preferences (vegetarian, vegan, gluten-free, etc.)"""
    __tablename__ = 'user_dietary_preferences'
    
    user_preference_id = Column(String(36), ForeignKey('user_preferences.id', ondelete='CASCADE'), nullable=False)
    preference = Column(String(50), nullable=False)  # vegetarian, vegan, gluten_free, etc.
    
    # Indexes
    __table_args__ = (
        Index('idx_dietary_preference', 'user_preference_id'),
    )
    
    # Relationships
    preference = relationship("UserPreference", back_populates="dietary_preferences")


class UserHealthCondition(Base, BaseMixin):
    """Health conditions (diabetes, hypertension, etc.)"""
    __tablename__ = 'user_health_conditions'
    
    user_preference_id = Column(String(36), ForeignKey('user_preferences.id', ondelete='CASCADE'), nullable=False)
    condition = Column(String(100), nullable=False)  # diabetes, hypertension, etc.
    
    # Indexes
    __table_args__ = (
        Index('idx_health_condition', 'user_preference_id'),
    )
    
    # Relationships
    preference = relationship("UserPreference", back_populates="health_conditions")


class UserAllergy(Base, BaseMixin):
    """Food allergies (nuts, dairy, shellfish, etc.)"""
    __tablename__ = 'user_allergies'
    
    user_preference_id = Column(String(36), ForeignKey('user_preferences.id', ondelete='CASCADE'), nullable=False)
    allergen = Column(String(100), nullable=False)  # nuts, dairy, shellfish, etc.
    
    # Indexes
    __table_args__ = (
        Index('idx_allergen', 'user_preference_id'),
    )
    
    # Relationships
    preference = relationship("UserPreference", back_populates="allergies")


class UserGoal(Base, BaseMixin):
    """Tracks user fitness goals and activity levels over time."""
    __tablename__ = 'user_goals'
    
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_level = Column(String(30), nullable=False)  # sedentary, light, moderate, active, extra
    fitness_goal = Column(String(30), nullable=False)  # maintenance, cutting, bulking
    target_weight_kg = Column(Float, nullable=True)
    meals_per_day = Column(Integer, default=3, nullable=False)
    snacks_per_day = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('target_weight_kg IS NULL OR target_weight_kg > 0', name='check_target_weight_positive'),
        CheckConstraint('meals_per_day >= 1 AND meals_per_day <= 10', name='check_meals_per_day_range'),
        CheckConstraint('snacks_per_day >= 0 AND snacks_per_day <= 10', name='check_snacks_per_day_range'),
        Index('idx_user_goal_current', 'user_id', 'is_current'),
    )
    
    # Relationships
    user = relationship("User", back_populates="goals")
    tdee_calculations = relationship("TdeeCalculation", back_populates="goal")