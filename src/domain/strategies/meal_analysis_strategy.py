import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class MealAnalysisStrategy(ABC):
    """
    Abstract base class for meal analysis strategies.
    
    This implements the Strategy pattern for different types of context-aware
    meal analysis (basic, portion-aware, ingredient-aware, etc.)
    """
    
    @abstractmethod
    def get_analysis_prompt(self) -> str:
        """
        Get the system prompt for this analysis strategy.
        
        Returns:
            str: The system prompt text
        """
        pass
    
    @abstractmethod
    def get_user_message(self) -> str:
        """
        Get the user message for this analysis strategy.
        
        Returns:
            str: The user message text with context
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of this strategy for logging.
        
        Returns:
            str: Strategy name
        """
        pass

