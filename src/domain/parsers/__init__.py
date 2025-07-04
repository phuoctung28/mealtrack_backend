"""
Domain parsers for external data.

This package contains parsers for converting external data formats
(like GPT responses) into domain models.
"""
from .gpt_response_parser import GPTResponseParser, GPTResponseParsingError

__all__ = [
    'GPTResponseParser',
    'GPTResponseParsingError'
]