from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum
import uuid


class ConversationState(str, Enum):
    GREETING = "greeting"
    ASKING_DIETARY_PREFERENCES = "asking_dietary_preferences"
    ASKING_ALLERGIES = "asking_allergies"
    ASKING_FITNESS_GOALS = "asking_fitness_goals"
    ASKING_MEAL_COUNT = "asking_meal_count"
    ASKING_PLAN_DURATION = "asking_plan_duration"
    ASKING_COOKING_TIME = "asking_cooking_time"
    ASKING_CUISINE_PREFERENCES = "asking_cuisine_preferences"
    CONFIRMING_PREFERENCES = "confirming_preferences"
    GENERATING_PLAN = "generating_plan"
    SHOWING_PLAN = "showing_plan"
    ADJUSTING_MEAL = "adjusting_meal"
    COMPLETED = "completed"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a single message in the conversation"""
    message_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[Dict] = None
    
    def __init__(self, role: MessageRole, content: str, metadata: Optional[Dict] = None):
        self.message_id = str(uuid.uuid4())
        self.role = role
        self.content = content
        self.timestamp = datetime.utcnow()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ConversationContext:
    """Stores the context of the meal planning conversation"""
    dietary_preferences: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    fitness_goal: Optional[str] = None
    meals_per_day: Optional[int] = None
    snacks_per_day: Optional[int] = None
    plan_duration: Optional[str] = None
    cooking_time_weekday: Optional[int] = None
    cooking_time_weekend: Optional[int] = None
    favorite_cuisines: Optional[List[str]] = None
    disliked_ingredients: Optional[List[str]] = None
    current_meal_plan: Optional[str] = None  # meal_plan_id
    
    def is_complete(self) -> bool:
        """Check if all required information has been collected"""
        required_fields = [
            self.dietary_preferences is not None,
            self.allergies is not None,
            self.fitness_goal is not None,
            self.meals_per_day is not None,
            self.plan_duration is not None,
            self.cooking_time_weekday is not None,
            self.cooking_time_weekend is not None,
            self.favorite_cuisines is not None,
            self.disliked_ingredients is not None
        ]
        return all(required_fields)
    
    def to_dict(self) -> Dict:
        return {
            "dietary_preferences": self.dietary_preferences,
            "allergies": self.allergies,
            "fitness_goal": self.fitness_goal,
            "meals_per_day": self.meals_per_day,
            "snacks_per_day": self.snacks_per_day,
            "plan_duration": self.plan_duration,
            "cooking_time_weekday": self.cooking_time_weekday,
            "cooking_time_weekend": self.cooking_time_weekend,
            "favorite_cuisines": self.favorite_cuisines,
            "disliked_ingredients": self.disliked_ingredients,
            "current_meal_plan": self.current_meal_plan
        }


@dataclass
class Conversation:
    """Represents a meal planning conversation session"""
    conversation_id: str
    user_id: str
    state: ConversationState
    context: ConversationContext
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    
    def __init__(self, user_id: str):
        self.conversation_id = str(uuid.uuid4())
        self.user_id = user_id
        self.state = ConversationState.GREETING
        self.context = ConversationContext()
        self.messages = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict] = None) -> Message:
        message = Message(role, content, metadata)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message
    
    def update_state(self, new_state: ConversationState):
        self.state = new_state
        self.updated_at = datetime.utcnow()
    
    def get_last_assistant_message(self) -> Optional[Message]:
        for message in reversed(self.messages):
            if message.role == MessageRole.ASSISTANT:
                return message
        return None
    
    def get_conversation_history(self) -> List[Dict]:
        return [msg.to_dict() for msg in self.messages]
    
    def to_dict(self) -> Dict:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "context": self.context.to_dict(),
            "messages": self.get_conversation_history(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }