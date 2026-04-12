"""Result model for food image search (NM-72)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FoodImageResult:
    """A resolved food photo from an external image provider."""

    url: str            # Full-size URL (~560px wide for Pexels medium)
    thumbnail_url: str  # Small thumbnail URL
    source: str         # "pexels" | "unsplash"
    photographer: Optional[str] = None
