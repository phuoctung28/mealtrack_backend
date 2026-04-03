"""Response schemas for meal discovery endpoints."""
from typing import List, Optional

from pydantic import BaseModel


class DiscoveryMealResponse(BaseModel):
    id: str
    name: str
    name_en: str
    emoji: str
    cuisine: str
    calories: int
    protein: float
    carbs: float
    fat: float
    ingredients: List[str]
    image_search_query: str
    image_url: Optional[str] = None
    image_source: Optional[str] = None


class DiscoveryBatchResponse(BaseModel):
    meals: List[DiscoveryMealResponse]
    batch_id: str       # Discovery session ID for next-page requests
    has_more: bool = True


class FoodImageResponse(BaseModel):
    url: str
    thumbnail_url: str
    source: str                        # "pexels" | "unsplash"
    photographer: Optional[str] = None


class FoodPreferencesResponse(BaseModel):
    allergies: List[str] = []
    dietary_preferences: List[str] = []
    disliked_foods: List[str] = []


class UpdateFoodPreferencesRequest(BaseModel):
    allergies: List[str] = []
    dietary_preferences: List[str] = []
    disliked_foods: List[str] = []
