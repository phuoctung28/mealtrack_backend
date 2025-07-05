"""
Query handlers for user domain - read operations.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.handlers.command_handlers.user_command_handlers import SaveUserOnboardingCommandHandler
from src.app.events.base import EventHandler, handles
from src.app.queries.user import (
    GetOnboardingSectionsQuery,
    GetUserProfileQuery
)
from src.infra.database.models.user.profile import UserProfile

logger = logging.getLogger(__name__)


@handles(GetOnboardingSectionsQuery)
class GetOnboardingSectionsQueryHandler(EventHandler[GetOnboardingSectionsQuery, Dict[str, Any]]):
    """Handler for getting onboarding sections structure."""
    
    def __init__(self):
        pass
    
    def set_dependencies(self):
        """No dependencies needed for this handler."""
        pass
    
    async def handle(self, query: GetOnboardingSectionsQuery) -> Dict[str, Any]:
        """Get onboarding sections structure."""
        return {
            "sections": [
                {
                    "id": "personal_info",
                    "title": "Personal Information",
                    "description": "Basic information about yourself",
                    "fields": [
                        {
                            "name": "age",
                            "type": "number",
                            "label": "Age",
                            "required": True,
                            "min": 1,
                            "max": 120
                        },
                        {
                            "name": "gender",
                            "type": "select",
                            "label": "Gender",
                            "required": True,
                            "options": ["male", "female"]
                        },
                        {
                            "name": "height_cm",
                            "type": "number",
                            "label": "Height (cm)",
                            "required": True,
                            "min": 50,
                            "max": 300
                        },
                        {
                            "name": "weight_kg",
                            "type": "number",
                            "label": "Weight (kg)",
                            "required": True,
                            "min": 20,
                            "max": 500
                        },
                        {
                            "name": "body_fat_percentage",
                            "type": "number",
                            "label": "Body Fat % (optional)",
                            "required": False,
                            "min": 1,
                            "max": 60
                        }
                    ]
                },
                {
                    "id": "goals",
                    "title": "Your Goals",
                    "description": "What you want to achieve",
                    "fields": [
                        {
                            "name": "activity_level",
                            "type": "select",
                            "label": "Activity Level",
                            "required": True,
                            "options": [
                                {"value": "sedentary", "label": "Sedentary (little or no exercise)"},
                                {"value": "lightly_active", "label": "Lightly Active (1-3 days/week)"},
                                {"value": "moderately_active", "label": "Moderately Active (3-5 days/week)"},
                                {"value": "very_active", "label": "Very Active (6-7 days/week)"},
                                {"value": "extra_active", "label": "Extra Active (physical job + exercise)"}
                            ]
                        },
                        {
                            "name": "fitness_goal",
                            "type": "select",
                            "label": "Fitness Goal",
                            "required": True,
                            "options": [
                                {"value": "lose_weight", "label": "Lose Weight"},
                                {"value": "maintain_weight", "label": "Maintain Weight"},
                                {"value": "gain_weight", "label": "Gain Weight"},
                                {"value": "build_muscle", "label": "Build Muscle"}
                            ]
                        },
                        {
                            "name": "target_weight_kg",
                            "type": "number",
                            "label": "Target Weight (kg)",
                            "required": False,
                            "min": 20,
                            "max": 500
                        },
                        {
                            "name": "meals_per_day",
                            "type": "number",
                            "label": "Meals Per Day",
                            "required": True,
                            "min": 1,
                            "max": 6,
                            "default": 3
                        },
                        {
                            "name": "snacks_per_day",
                            "type": "number",
                            "label": "Snacks Per Day",
                            "required": True,
                            "min": 0,
                            "max": 5,
                            "default": 1
                        }
                    ]
                },
                {
                    "id": "preferences",
                    "title": "Dietary Preferences",
                    "description": "Your dietary restrictions and preferences",
                    "fields": [
                        {
                            "name": "dietary_preferences",
                            "type": "multiselect",
                            "label": "Dietary Preferences",
                            "required": False,
                            "options": [
                                "vegetarian",
                                "vegan",
                                "pescatarian",
                                "keto",
                                "paleo",
                                "gluten_free",
                                "dairy_free",
                                "low_carb",
                                "high_protein"
                            ]
                        },
                        {
                            "name": "health_conditions",
                            "type": "multiselect",
                            "label": "Health Conditions",
                            "required": False,
                            "options": [
                                "diabetes",
                                "hypertension",
                                "high_cholesterol",
                                "heart_disease",
                                "celiac_disease",
                                "lactose_intolerance",
                                "ibs"
                            ]
                        },
                        {
                            "name": "allergies",
                            "type": "multiselect",
                            "label": "Allergies",
                            "required": False,
                            "options": [
                                "nuts",
                                "shellfish",
                                "eggs",
                                "dairy",
                                "soy",
                                "wheat",
                                "fish",
                                "sesame"
                            ]
                        }
                    ]
                }
            ]
        }


@handles(GetUserProfileQuery)
class GetUserProfileQueryHandler(EventHandler[GetUserProfileQuery, Dict[str, Any]]):
    """Handler for getting user profile with TDEE calculation."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db
    
    async def handle(self, query: GetUserProfileQuery) -> Dict[str, Any]:
        """Get user profile with calculated TDEE."""
        if not self.db:
            raise RuntimeError("Database session not configured")
        
        # Get user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == query.user_id
        ).first()
        
        if not profile:
            raise ResourceNotFoundException(f"Profile for user {query.user_id} not found")
        
        # Calculate TDEE
        handler = SaveUserOnboardingCommandHandler(self.db)
        tdee_result = handler._calculate_tdee_and_macros(profile)
        
        return {
            "profile": {
                "id": profile.id,
                "user_id": profile.user_id,
                "age": profile.age,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "body_fat_percentage": profile.body_fat_percentage,
                "activity_level": profile.activity_level,
                "fitness_goal": profile.fitness_goal,
                "target_weight_kg": profile.target_weight_kg,
                "meals_per_day": profile.meals_per_day,
                "snacks_per_day": profile.snacks_per_day,
                "dietary_preferences": profile.dietary_preferences or [],
                "health_conditions": profile.health_conditions or [],
                "allergies": profile.allergies or [],
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
            },
            "tdee": tdee_result
        }