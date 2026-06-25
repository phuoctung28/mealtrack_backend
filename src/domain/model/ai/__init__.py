"""
AI bounded context - Domain models for GPT/AI interactions.
"""

from .gpt_response import GPTAnalysisResponse, GPTFoodItem, GPTMacros
from .gpt_response_errors import (
    GPTResponseError,
    GPTResponseFormatError,
    GPTResponseIncompleteError,
    GPTResponseParsingError,
    GPTResponseValidationError,
)
from .model_purpose import ModelPurpose
from .nutrition_contracts import (
    AINutritionMacros,
    MealTextFoodEstimate,
    MealTextNutritionResponse,
    VisionFoodEstimate,
    VisionNutritionResponse,
)

__all__ = [
    "AINutritionMacros",
    "MealTextFoodEstimate",
    "MealTextNutritionResponse",
    "GPTMacros",
    "GPTFoodItem",
    "GPTAnalysisResponse",
    "GPTResponseError",
    "GPTResponseFormatError",
    "GPTResponseValidationError",
    "GPTResponseParsingError",
    "GPTResponseIncompleteError",
    "VisionFoodEstimate",
    "VisionNutritionResponse",
    "ModelPurpose",
]
