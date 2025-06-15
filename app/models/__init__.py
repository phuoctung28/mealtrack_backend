"""
Application Models Package

This package contains application-specific data structures and value objects
used across multiple application services. These are pure data models without 
business logic - the logic belongs in app/services.

Structure:
- common.py: Common application data models and value objects
- Pure data structures for application layer use
- Models that provide structure for data flow between layers
"""

# Common application data models
from .common import (
    MacrosSchema,
    NutritionSummarySchema,
    PaginationMetadata,
    StatusSchema,
    AnalysisContext
)

__all__ = [
    # Common data models
    "MacrosSchema",
    "NutritionSummarySchema", 
    "PaginationMetadata",
    "StatusSchema",
    "AnalysisContext"
] 