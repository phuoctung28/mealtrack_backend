"""
AI bounded context - Domain models for GPT/AI interactions.
"""
from .gpt_response import GPTMacros, GPTFoodItem, GPTAnalysisResponse
from .gpt_response_errors import (
    GPTResponseError,
    GPTResponseFormatError,
    GPTResponseValidationError,
    GPTResponseParsingError,
    GPTResponseIncompleteError,
)

__all__ = [
    'GPTMacros',
    'GPTFoodItem',
    'GPTAnalysisResponse',
    'GPTResponseError',
    'GPTResponseFormatError',
    'GPTResponseValidationError',
    'GPTResponseParsingError',
    'GPTResponseIncompleteError',
]

