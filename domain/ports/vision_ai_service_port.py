from abc import ABC, abstractmethod
from typing import Dict, Any, List


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

    @abstractmethod
    def analyze_with_ingredients_context(self, image_bytes: bytes, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a food image to extract nutritional information.

        Args:
            image_bytes: The raw bytes of the image to analyze

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
            :param image_bytes:
            :param ingredients:
        """
        pass

    @abstractmethod
    def analyze_with_portion_context(self, image_bytes: bytes, portion_size: float, unit: str) -> Dict[str, Any]:
        """
        Analyze a food image to extract nutritional information.

        Args:
            image_bytes: The raw bytes of the image to analyze

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
            :param image_bytes:
            :param unit:
            :param portion_size:
        """
        pass

    @abstractmethod
    def analyze_with_weight_context(self, image_bytes: bytes, weight_grams: float) -> Dict[str, Any]:
        """
        Analyze a food image with specific weight context for accurate nutrition.

        Args:
            image_bytes: The raw bytes of the image to analyze
            weight_grams: The target weight in grams

        Returns:
            JSON-compatible dictionary with the raw AI response

        Raises:
            RuntimeError: If analysis fails
        """
        pass