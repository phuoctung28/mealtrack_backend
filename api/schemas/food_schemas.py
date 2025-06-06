from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class MacrosSchema(BaseModel):
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams") 
    fat: float = Field(..., ge=0, description="Fat in grams")
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in grams")

class MicrosSchema(BaseModel):
    vitamin_a: Optional[float] = Field(None, ge=0)
    vitamin_c: Optional[float] = Field(None, ge=0)
    calcium: Optional[float] = Field(None, ge=0)
    iron: Optional[float] = Field(None, ge=0)
    sodium: Optional[float] = Field(None, ge=0)
    potassium: Optional[float] = Field(None, ge=0)

class CreateFoodRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Food name")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    description: Optional[str] = Field(None, max_length=500, description="Food description")
    serving_size: Optional[float] = Field(None, gt=0, description="Serving size")
    serving_unit: Optional[str] = Field(None, max_length=50, description="Serving unit (e.g., 'cup', 'piece')")
    calories_per_serving: Optional[float] = Field(None, ge=0, description="Calories per serving")
    macros_per_serving: Optional[MacrosSchema] = Field(None, description="Macros per serving")
    micros_per_serving: Optional[MicrosSchema] = Field(None, description="Micros per serving")
    barcode: Optional[str] = Field(None, max_length=50, description="Product barcode")
    image_url: Optional[str] = Field(None, max_length=500, description="Image URL")

class UpdateFoodRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Food name")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    description: Optional[str] = Field(None, max_length=500, description="Food description")
    serving_size: Optional[float] = Field(None, gt=0, description="Serving size")
    serving_unit: Optional[str] = Field(None, max_length=50, description="Serving unit")
    calories_per_serving: Optional[float] = Field(None, ge=0, description="Calories per serving")
    macros_per_serving: Optional[MacrosSchema] = Field(None, description="Macros per serving")
    micros_per_serving: Optional[MicrosSchema] = Field(None, description="Micros per serving")
    barcode: Optional[str] = Field(None, max_length=50, description="Product barcode")
    image_url: Optional[str] = Field(None, max_length=500, description="Image URL")

class UpdateFoodMacrosRequest(BaseModel):
    size: Optional[float] = Field(None, gt=0, description="Size/amount of food")
    amount: Optional[float] = Field(None, gt=0, description="Amount of food")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measurement")
    
    @validator('size', 'amount')
    def at_least_one_required(cls, v, values):
        if v is None and values.get('size') is None and values.get('amount') is None:
            raise ValueError('At least one of size or amount must be provided')
        return v

class FoodResponse(BaseModel):
    food_id: str
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    serving_size: Optional[float] = None
    serving_unit: Optional[str] = None
    calories_per_serving: Optional[float] = None
    macros_per_serving: Optional[MacrosSchema] = None
    micros_per_serving: Optional[MicrosSchema] = None
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    is_verified: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class FoodPhotoRequest(BaseModel):
    # This will be handled as UploadFile in the endpoint
    pass

class FoodPhotoResponse(BaseModel):
    food_name: str
    confidence: float = Field(..., ge=0, le=1)
    macros: MacrosSchema
    calories: float = Field(..., ge=0)
    analysis_id: str  # For tracking the analysis

class PaginatedFoodResponse(BaseModel):
    foods: List[FoodResponse]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int

class FoodSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(10, ge=1, le=100)
    include_ingredients: bool = Field(False, description="Include ingredients in search")

class FoodSearchResponse(BaseModel):
    results: List[FoodResponse]
    query: str
    total_results: int 