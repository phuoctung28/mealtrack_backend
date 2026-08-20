"""Domain model for meal-scan visual identity matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class MealScanVisualIdentity:
    """Angle-tolerant fingerprint for a user's scanned meal photo."""

    id: str
    user_id: str
    meal_id: str
    source: str
    dish_slug: str
    ingredients: tuple[str, ...] = field(default_factory=tuple)
    container: str | None = None
    background: str | None = None
    identity_key: str = ""
    scene_signature: tuple[float, ...] = field(default_factory=tuple)
    created_at: datetime | None = None


@dataclass(frozen=True)
class ParsedVisualIdentity:
    """Parsed lightweight vision identity for a photo."""

    dish_slug: str
    ingredients: tuple[str, ...]
    container: str | None
    background: str | None
    identity_key: str
    is_food: bool = True
    confidence: float = 0.0
