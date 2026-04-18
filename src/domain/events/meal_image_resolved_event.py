"""Domain event: nightly job finished resolving an image for a meal name."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class MealImageResolvedEvent:
    aggregate_id: str  # name_slug
    meal_name: str
    image_url: str
    source: str  # pexels | unsplash | ai_generated | failed
    confidence: Optional[float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid4()))
