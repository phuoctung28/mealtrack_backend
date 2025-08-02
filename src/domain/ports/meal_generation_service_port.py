"""
Port for meal generation services following clean architecture.
Single LLM service that handles different prompts and request data.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class MealGenerationServicePort(ABC):
    """Unified port for all meal generation using single LLM with different prompts."""
    
    @abstractmethod
    def generate_meal_plan(self, prompt: str, system_message: str, response_type: str = "json") -> Dict[str, Any]:
        """
        Generate meal plan using provided prompt and system message.
        
        Args:
            prompt: The meal generation prompt
            system_message: System message for the LLM
            response_type: Expected response type ("json" or "text")
            
        Returns:
            Generated meal plan data
        """
        pass