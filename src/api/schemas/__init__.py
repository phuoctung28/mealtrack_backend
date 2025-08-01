"""
API Schemas module - Request and Response DTOs.

This module provides a clean import structure for all API schemas,
organized into request and response categories following clean architecture.
"""

# Re-export all request schemas
from .request import *

# Re-export all response schemas  
from .response import *

# Keep backward compatibility for existing imports
# These will be deprecated in future versions
ErrorResponse = MealSuggestionErrorResponse  # Alias for backward compatibility