"""Result model for food image search (NM-72)."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FoodImageResult:
    """A resolved food photo from an external image provider."""

    url: str  # Full-size URL (~560px wide for Pexels medium)
    thumbnail_url: str  # Small thumbnail URL
    source: str  # "pexels" | "unsplash"
    photographer: Optional[str] = None
    photographer_url: Optional[str] = None  # Profile URL with UTM params
    download_location: Optional[str] = None  # Unsplash download trigger URL
    alt_text: Optional[str] = None  # Image description for relevance validation
    confidence: float = 0.5  # 0.0-1.0 how well image matches query
