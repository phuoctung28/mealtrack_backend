from abc import ABC, abstractmethod
from typing import Dict, Any

class VisionAIServicePort(ABC):
    """
    Port interface for AI vision services that can analyze food images.
    
    Uses the Strategy pattern - one analyze method that accepts different analysis strategies.
    """
    
    @abstractmethod
    def analyze(self, image_bytes: bytes, strategy=None) -> Dict[str, Any]:
        """
        Analyze a food image using the provided strategy.
        
        Args:
            image_bytes: The raw bytes of the image to analyze
            strategy: Analysis strategy to use (optional, defaults to basic analysis)
            
        Returns:
            JSON-compatible dictionary with the raw AI response
            
        Raises:
            RuntimeError: If analysis fails
        """
        pass 