from abc import ABC, abstractmethod
from typing import Dict, Any

class VisionAIServicePort(ABC):
    """
    Port interface for AI vision services that can analyze food images.
    
    This port is used by the application layer to interact with vision AI services
    like OpenAI Vision API.
    """
    
    @abstractmethod
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze a food image to extract nutritional information.
        
        Args:
            image_bytes: The raw bytes of the image to analyze
            
        Returns:
            JSON-compatible dictionary with the raw AI response
            
        Raises:
            RuntimeError: If analysis fails
        """
        pass 