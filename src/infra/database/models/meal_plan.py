from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class DietaryPreferenceEnum(str, enum.Enum):
    vegan = "vegan"
    vegetarian = "vegetarian"
    pescatarian = "pescatarian"
    gluten_free = "gluten_free"
    keto = "keto"
    paleo = "paleo"
    low_carb = "low_carb"
    dairy_free = "dairy_free"
    none = "none"


class FitnessGoalEnum(str, enum.Enum):
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"
    general_health = "general_health"


class MealTypeEnum(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class PlanDurationEnum(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"


class ConversationStateEnum(str, enum.Enum):
    greeting = "greeting"
    asking_dietary_preferences = "asking_dietary_preferences"
    asking_allergies = "asking_allergies"
    asking_fitness_goals = "asking_fitness_goals"
    asking_meal_count = "asking_meal_count"
    asking_plan_duration = "asking_plan_duration"
    asking_cooking_time = "asking_cooking_time"
    asking_cuisine_preferences = "asking_cuisine_preferences"
    confirming_preferences = "confirming_preferences"
    generating_plan = "generating_plan"
    showing_plan = "showing_plan"
    adjusting_meal = "adjusting_meal"
    completed = "completed"


class MealPlan(Base, BaseMixin):
    __tablename__ = "meal_plans"
    
    user_id = Column(String(255), nullable=False, index=True)
    
    # User preferences stored as JSON
    dietary_preferences = Column(JSON)
    allergies = Column(JSON)
    fitness_goal = Column(Enum(FitnessGoalEnum))
    meals_per_day = Column(Integer)
    snacks_per_day = Column(Integer)
    cooking_time_weekday = Column(Integer)
    cooking_time_weekend = Column(Integer)
    favorite_cuisines = Column(JSON)
    disliked_ingredients = Column(JSON)
    plan_duration = Column(Enum(PlanDurationEnum))
    
    # Relationships
    days = relationship("MealPlanDay", back_populates="meal_plan", cascade="all, delete-orphan")


class MealPlanDay(Base, BaseMixin):
    __tablename__ = "meal_plan_days"
    meal_plan_id = Column(String(36), ForeignKey("meal_plans.id"), nullable=False)
    date = Column(Date, nullable=False)
    
    # Relationships
    meal_plan = relationship("MealPlan", back_populates="days")
    meals = relationship("PlannedMeal", back_populates="day", cascade="all, delete-orphan")


class PlannedMeal(Base, BaseMixin):
    __tablename__ = "planned_meals"
    day_id = Column(String(36), ForeignKey("meal_plan_days.id"), nullable=False)
    meal_type = Column(Enum(MealTypeEnum), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    prep_time = Column(Integer)  # minutes
    cook_time = Column(Integer)  # minutes
    
    # Nutrition info
    calories = Column(Integer)
    protein = Column(Float)
    carbs = Column(Float)
    fat = Column(Float)
    
    # Stored as JSON arrays
    ingredients = Column(JSON)
    instructions = Column(JSON)
    
    # Dietary flags
    is_vegetarian = Column(Boolean, default=False)
    is_vegan = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean, default=False)
    
    cuisine_type = Column(String(100))
    
    # Relationships
    day = relationship("MealPlanDay", back_populates="meals")


class Conversation(Base, BaseMixin):
    __tablename__ = "conversations"
    user_id = Column(String(255), nullable=False, index=True)
    state = Column(Enum(ConversationStateEnum), nullable=False)
    
    # Conversation context stored as JSON
    context = Column(JSON)
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base, BaseMixin):
    __tablename__ = "conversation_messages"
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")