import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union


class OnboardingSectionType(Enum):
    """Types of onboarding sections."""
    PERSONAL_INFO = "PERSONAL_INFO"
    FITNESS_GOALS = "FITNESS_GOALS"
    DIETARY_PREFERENCES = "DIETARY_PREFERENCES"
    ACTIVITY_LEVEL = "ACTIVITY_LEVEL"
    HEALTH_CONDITIONS = "HEALTH_CONDITIONS"

class FieldType(Enum):
    """Types of form fields."""
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    EMAIL = "EMAIL"
    SELECT = "SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    RADIO = "RADIO"
    CHECKBOX = "CHECKBOX"
    DATE = "DATE"
    SLIDER = "SLIDER"

@dataclass
class OnboardingField:
    """Represents a field in an onboarding section."""
    field_id: str
    label: str
    field_type: FieldType
    required: bool = True
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None  # For select/radio fields
    validation: Optional[Dict[str, Any]] = None  # Validation rules
    default_value: Optional[Union[str, int, float, bool]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "field_id": self.field_id,
            "label": self.label,
            "field_type": self.field_type.value,
            "required": self.required
        }
        
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.help_text:
            result["help_text"] = self.help_text
        if self.options:
            result["options"] = self.options
        if self.validation:
            result["validation"] = self.validation
        if self.default_value is not None:
            result["default_value"] = self.default_value
            
        return result

@dataclass
class OnboardingSection:
    """
    Domain model representing an onboarding section with its fields.
    """
    section_id: str
    title: str
    description: str
    section_type: OnboardingSectionType
    order: int
    fields: List[OnboardingField]
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID format
        try:
            uuid.UUID(self.section_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for section_id: {self.section_id}")
        
        if self.order < 0:
            raise ValueError(f"Order must be non-negative: {self.order}")
            
        if not self.fields:
            raise ValueError("Section must have at least one field")
    
    @classmethod
    def create_new(cls, title: str, description: str, section_type: OnboardingSectionType, order: int, fields: List[OnboardingField]) -> 'OnboardingSection':
        """Factory method to create a new onboarding section."""
        return cls(
            section_id=str(uuid.uuid4()),
            title=title,
            description=description,
            section_type=section_type,
            order=order,
            fields=fields,
            created_at=datetime.now()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "section_id": self.section_id,
            "title": self.title,
            "description": self.description,
            "section_type": self.section_type.value,
            "order": self.order,
            "fields": [field.to_dict() for field in self.fields],
            "is_active": self.is_active
        }
        
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
            
        return result

@dataclass
class OnboardingResponse:
    """
    Domain model representing a user's response to onboarding.
    """
    response_id: str
    user_id: Optional[str]  # For when user system is implemented
    section_id: str
    field_responses: Dict[str, Any]  # field_id -> value mapping
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID formats
        try:
            uuid.UUID(self.response_id)
            uuid.UUID(self.section_id)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {e}")
        
        if self.user_id:
            try:
                uuid.UUID(self.user_id)
            except ValueError:
                raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
    
    @classmethod
    def create_new(cls, section_id: str, field_responses: Dict[str, Any], user_id: Optional[str] = None) -> 'OnboardingResponse':
        """Factory method to create a new onboarding response."""
        return cls(
            response_id=str(uuid.uuid4()),
            user_id=user_id,
            section_id=section_id,
            field_responses=field_responses,
            completed_at=datetime.now(),
            created_at=datetime.now()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        result = {
            "response_id": self.response_id,
            "section_id": self.section_id,
            "field_responses": self.field_responses
        }
        
        if self.user_id:
            result["user_id"] = self.user_id
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
            
        return result 