from sqlalchemy import Column, String, Float, Date, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import date as date_type

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class TdeeCalculation(Base, BaseMixin):
    """Stores TDEE calculation history for tracking user progress."""
    __tablename__ = 'tdee_calculations'
    
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user_profile_id = Column(String(36), ForeignKey('user_profiles.id'), nullable=False)
    user_goal_id = Column(String(36), ForeignKey('user_goals.id'), nullable=False)
    
    # Calculation results
    bmr = Column(Float, nullable=False)
    tdee = Column(Float, nullable=False)
    target_calories = Column(Float, nullable=False)
    
    # Macro targets (SimpleMacroTargets)
    protein_grams = Column(Float, nullable=False)
    carbs_grams = Column(Float, nullable=False)
    fat_grams = Column(Float, nullable=False)
    
    calculation_date = Column(Date, default=date_type.today, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('bmr > 0', name='check_bmr_positive'),
        CheckConstraint('tdee > 0', name='check_tdee_positive'),
        CheckConstraint('target_calories > 0', name='check_target_calories_positive'),
        CheckConstraint('protein_grams >= 0', name='check_protein_non_negative'),
        CheckConstraint('carbs_grams >= 0', name='check_carbs_non_negative'),
        CheckConstraint('fat_grams >= 0', name='check_fat_non_negative'),
        Index('idx_user_date', 'user_id', 'calculation_date'),
    )
    
    # Relationships
    user = relationship("User", back_populates="tdee_calculations")
    profile = relationship("UserProfile", back_populates="tdee_calculations")
    goal = relationship("UserGoal", back_populates="tdee_calculations")
    
    @property
    def total_macro_calories(self):
        """Calculate total calories from macros."""
        return (self.protein_grams * 4) + (self.carbs_grams * 4) + (self.fat_grams * 9)