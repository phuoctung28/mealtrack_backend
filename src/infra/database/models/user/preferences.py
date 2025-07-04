"""
User preference models for dietary restrictions, health conditions, and allergies.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import SecondaryEntityMixin


class UserPreference(Base, SecondaryEntityMixin):
    """Stores user dietary preferences and health-related information."""
    __tablename__ = 'user_preferences'
    
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    dietary_preferences = relationship("UserDietaryPreference", back_populates="user_preference", cascade="all, delete-orphan")
    health_conditions = relationship("UserHealthCondition", back_populates="user_preference", cascade="all, delete-orphan")
    allergies = relationship("UserAllergy", back_populates="user_preference", cascade="all, delete-orphan")


class UserDietaryPreference(Base, SecondaryEntityMixin):
    """Dietary preferences (vegetarian, vegan, gluten-free, etc.)"""
    __tablename__ = 'user_dietary_preferences'
    
    user_preference_id = Column(Integer, ForeignKey('user_preferences.id', ondelete='CASCADE'), nullable=False)
    preference = Column(String(50), nullable=False)  # vegetarian, vegan, gluten_free, etc.
    
    # Indexes
    __table_args__ = (
        Index('idx_dietary_preference', 'user_preference_id'),
    )
    
    # Relationships
    user_preference = relationship("UserPreference", back_populates="dietary_preferences")


class UserHealthCondition(Base, SecondaryEntityMixin):
    """Health conditions (diabetes, hypertension, etc.)"""
    __tablename__ = 'user_health_conditions'
    
    user_preference_id = Column(Integer, ForeignKey('user_preferences.id', ondelete='CASCADE'), nullable=False)
    condition = Column(String(100), nullable=False)  # diabetes, hypertension, etc.
    
    # Indexes
    __table_args__ = (
        Index('idx_health_condition', 'user_preference_id'),
    )
    
    # Relationships
    user_preference = relationship("UserPreference", back_populates="health_conditions")


class UserAllergy(Base, SecondaryEntityMixin):
    """Food allergies (nuts, dairy, shellfish, etc.)"""
    __tablename__ = 'user_allergies'
    
    user_preference_id = Column(Integer, ForeignKey('user_preferences.id', ondelete='CASCADE'), nullable=False)
    allergen = Column(String(100), nullable=False)  # nuts, dairy, shellfish, etc.
    
    # Indexes
    __table_args__ = (
        Index('idx_allergen', 'user_preference_id'),
    )
    
    # Relationships
    user_preference = relationship("UserPreference", back_populates="allergies")