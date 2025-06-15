"""
Application Data Models

Application-specific data structures and value objects used across 
multiple application services. Pure data models without business logic.
"""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# ============================================================================
# Application Data Models (Pure Data Structures)
# ============================================================================

class MacrosSchema(BaseModel):
    """Macronutrient data model for application layer."""
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams") 
    fat: float = Field(..., ge=0, description="Fat in grams")
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in grams")


class NutritionSummarySchema(BaseModel):
    """Application nutrition summary data model."""
    meal_name: str = Field(..., description="Identified meal name")
    total_calories: float = Field(..., ge=0, description="Total calories for the portion")
    total_weight_grams: float = Field(..., gt=0, description="Total weight of the meal in grams")
    calories_per_100g: float = Field(..., ge=0, description="Calories per 100g")
    macros_per_100g: MacrosSchema = Field(..., description="Macronutrients per 100g")
    total_macros: MacrosSchema = Field(..., description="Total macronutrients for the portion")
    confidence_score: float = Field(..., ge=0, le=1, description="AI analysis confidence")


# ============================================================================
# Application Pagination Models
# ============================================================================

class PaginationMetadata(BaseModel):
    """Application pagination metadata."""
    current_page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None
    
    @classmethod
    def create(cls, current_page: int, page_size: int, total_items: int) -> 'PaginationMetadata':
        """Factory method for creating pagination metadata."""
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
        has_next = current_page < total_pages
        has_previous = current_page > 1
        
        return cls(
            current_page=current_page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            next_page=current_page + 1 if has_next else None,
            previous_page=current_page - 1 if has_previous else None
        )


# ============================================================================
# Application Status Models
# ============================================================================

class StatusSchema(BaseModel):
    """Application status data model."""
    status: str
    status_message: str
    error_message: Optional[str] = None


# ============================================================================
# Application Context Models
# ============================================================================

class AnalysisContext(BaseModel):
    """Context information for meal analysis workflows."""
    requested_weight_grams: Optional[float] = None
    original_weight_grams: Optional[float] = None
    analysis_preferences: Optional[Dict[str, Any]] = None
    dietary_restrictions: Optional[List[str]] = None 