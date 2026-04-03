"""Lightweight meal model for discovery browsing (NM-67)."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DiscoveryMeal:
    """
    Lightweight meal representation for the discovery grid.

    Does NOT include full recipe (steps, seasonings) — those are fetched
    on-demand when user selects a meal. image_search_query is always in English.
    """

    id: str
    name: str           # Localized display name
    name_en: str        # Always English (canonical reference)
    emoji: str
    cuisine: str
    calories: int
    protein: float
    carbs: float
    fat: float
    ingredients: List[str] = field(default_factory=list)
    image_search_query: str = ""   # English query for Pexels/Unsplash
    image_url: Optional[str] = None
    image_source: Optional[str] = None  # "pexels" | "unsplash"
