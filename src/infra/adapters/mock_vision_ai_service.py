"""
Mock Vision AI Service for testing.
"""
from typing import Dict, Any

from src.domain.ports.vision_ai_service_port import VisionAIServicePort


class MockVisionAIService(VisionAIServicePort):
    """Mock implementation of vision AI service for testing."""
    
    def __init__(self, mock_response: Dict[str, Any] = None):
        """Initialize with optional mock response."""
        self.mock_response = mock_response or self._default_response()
    
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """Return mock analysis result."""
        return self.mock_response
    
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
                            "fiber": 0
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
                            "fiber": 2
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
                            "fiber": 4
                        }
                    }
                ],
                "macros": {
                    "protein": 48,
                    "carbs": 70,
                    "fat": 17,
                    "fiber": 6
                }
            },
            "raw_response": "Mock AI response for testing"
        }