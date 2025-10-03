"""
Custom exceptions for GPT response parsing.

This module defines specific exception types for different parsing failures,
improving error handling and debugging.
"""


class GPTResponseParsingError(GPTResponseError):
    """
    Raised when parsing the GPT response fails.
    
    This includes JSON parsing errors, type conversion errors, etc.
    """
    pass

