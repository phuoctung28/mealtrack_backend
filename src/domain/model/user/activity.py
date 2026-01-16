import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from src.domain.utils.timezone_utils import utc_now


class ActivityType(Enum):
    """Types of activities that can be tracked."""
    MEAL_SCAN = "MEAL_SCAN"
    MANUAL_FOOD_ADD = "MANUAL_FOOD_ADD"
    FOOD_UPDATE = "FOOD_UPDATE"
    INGREDIENT_ADD = "INGREDIENT_ADD"
    MACRO_CALCULATION = "MACRO_CALCULATION"

@dataclass
class Activity:
    """
    Domain model representing a user activity in the meal tracking system.
    """
    activity_id: str
    user_id: Optional[str]  # For when user system is implemented
    activity_type: ActivityType
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Store activity-specific data
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID format
        try:
            uuid.UUID(self.activity_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for activity_id: {self.activity_id}")
        
        if self.user_id:
            try:
                uuid.UUID(self.user_id)
            except ValueError:
                raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
    
    @classmethod
    def create_new(cls, activity_type: ActivityType, title: str, **kwargs) -> 'Activity':
        """Factory method to create a new activity."""
        return cls(
            activity_id=str(uuid.uuid4()),
            activity_type=activity_type,
            title=title,
            created_at=utc_now(),
            **kwargs
        )
    
    @classmethod
    def create_meal_scan_activity(cls, meal_id: str, food_names: list) -> 'Activity':
        """Create an activity for meal scanning."""
        return cls.create_new(
            activity_type=ActivityType.MEAL_SCAN,
            title=f"Scanned meal with {len(food_names)} items",
            description=f"Identified: {', '.join(food_names)}",
            metadata={
                "meal_id": meal_id,
                "food_names": food_names,
                "food_count": len(food_names)
            }
        )
    
    @classmethod
    def create_manual_food_activity(cls, food_id: str, food_name: str) -> 'Activity':
        """Create an activity for manual food addition."""
        return cls.create_new(
            activity_type=ActivityType.MANUAL_FOOD_ADD,
            title=f"Added {food_name} manually",
            description=f"Manually added food item: {food_name}",
            metadata={
                "food_id": food_id,
                "food_name": food_name
            }
        )
    
    @classmethod
    def create_food_update_activity(cls, food_id: str, food_name: str, updated_fields: list) -> 'Activity':
        """Create an activity for food updates."""
        return cls.create_new(
            activity_type=ActivityType.FOOD_UPDATE,
            title=f"Updated {food_name}",
            description=f"Updated fields: {', '.join(updated_fields)}",
            metadata={
                "food_id": food_id,
                "food_name": food_name,
                "updated_fields": updated_fields
            }
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "activity_id": self.activity_id,
            "activity_type": self.activity_type.value,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if self.user_id:
            result["user_id"] = self.user_id
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result 