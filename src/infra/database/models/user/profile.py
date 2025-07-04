"""
User profile model for physical attributes and personal information.
"""
from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey, Index, CheckConstraint
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