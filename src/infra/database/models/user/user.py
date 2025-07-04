"""
Core user model for authentication and account management.
"""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class User(Base, BaseMixin):
    """Core user table for authentication and account management."""
    __tablename__ = 'users'
    
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
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