"""
Mock Vision AI Service for testing.
"""
from typing import Dict, Any, List

from src.domain.ports.vision_ai_service_port import VisionAIServicePort


class MockVisionAIService(VisionAIServicePort):
    """Mock implementation of vision AI service for testing."""
    
    def __init__(self, mock_response: Dict[str, Any] = None):
        """Initialize with optional mock response."""
        self.mock_response = mock_response or self._default_response()
    
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """Return mock analysis result."""
        return self.mock_response
    
    def analyze_with_ingredients_context(self, image_bytes: bytes, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return mock analysis result with ingredients context."""
        response = self.mock_response.copy()
        # Add ingredients to the response if provided
        if ingredients:
            response["ingredients_context"] = ingredients
        return response
    
    def analyze_with_portion_context(self, image_bytes: bytes, portion_size: float, unit: str) -> Dict[str, Any]:
        """Return mock analysis result with portion context."""
        response = self.mock_response.copy()
        response["portion_context"] = {
            "portion_size": portion_size,
            "unit": unit
        }
        return response
    
    def analyze_with_weight_context(self, image_bytes: bytes, weight_grams: float) -> Dict[str, Any]:
        """Return mock analysis result with weight context."""
        response = self.mock_response.copy()
        response["weight_context"] = {
            "weight_grams": weight_grams
        }
        # Adjust calories based on weight (100g baseline)
        if "structured_data" in response:
            weight_factor = weight_grams / 100.0
            response["structured_data"]["total_calories"] = int(response["structured_data"]["total_calories"] * weight_factor)
            for food in response["structured_data"].get("foods", []):
                food["calories"] = int(food["calories"] * weight_factor)
        return response
    
    def _default_response(self) -> Dict[str, Any]:
        """Default mock response for meal analysis."""
        return {
            "structured_data": {
                "dish_name": "Grilled Chicken with Rice",
                "total_calories": 650,
                "confidence": 0.92,
                "foods": [
                    {
                        "name": "Grilled Chicken Breast",
                        "quantity": 150,
                        "unit": "g",
                        "calories": 250,
                        "confidence": 0.95,
                        "macros": {
                            "protein": 40,
                            "carbs": 0,
                            "fat": 8,
                        }
                    },
                    {
                        "name": "White Rice",
                        "quantity": 200,
                        "unit": "g",
                        "calories": 260,
                        "confidence": 0.90,
                        "macros": {
                            "protein": 5,
                            "carbs": 55,
                            "fat": 1,
                        }
                    },
                    {
                        "name": "Mixed Vegetables",
                        "quantity": 100,
                        "unit": "g",
                        "calories": 140,
                        "confidence": 0.88,
                        "macros": {
                            "protein": 3,
                            "carbs": 15,
                            "fat": 8,
                        }
                    }
                ],
                "macros": {
                    "protein": 48,
                    "carbs": 70,
                    "fat": 17,
                }
            },
            "raw_response": "Mock AI response for testing"
        }