"""
Custom exceptions for GPT response parsing.

This module defines specific exception types for different parsing failures,
improving error handling and debugging.
"""
from typing import Optional, Dict, Any


class GPTResponseError(Exception):
    """Base exception for all GPT response parsing errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class GPTResponseFormatError(GPTResponseError):
    """
    Raised when the GPT response format is invalid.
    
    This includes missing required fields, wrong structure, etc.
    """
    pass


class GPTResponseValidationError(GPTResponseError):
    """
    Raised when GPT response values fail validation.
    
    This includes out-of-range values, invalid types, etc.
    """
    pass


class GPTResponseParsingError(GPTResponseError):
    """
    Raised when parsing the GPT response fails.
    
    This includes JSON parsing errors, type conversion errors, etc.
    """
    pass


class GPTResponseIncompleteError(GPTResponseError):
    """
    Raised when the GPT response is incomplete or truncated.
    
    This can happen when the response is cut off due to token limits.
    """
    pass


class GPTResponseConfidenceError(GPTResponseError):
    """
    Raised when the GPT response confidence is too low.
    
    This allows handling of low-confidence responses differently.
    """
    
    def __init__(self, message: str, confidence: float, threshold: float = 0.5):
        super().__init__(message, {
            "confidence": confidence,
            "threshold": threshold
        })
        self.confidence = confidence
        self.threshold = threshold