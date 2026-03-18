"""
Vietnamese text normalization and macro validation utilities.
Used by all scrapers to produce consistent FoodEntry values.
"""
import logging
import unicodedata

from .categories import CATEGORY_MAP
from .schema import FoodEntry

logger = logging.getLogger(__name__)


def normalize_vi_name(text: str) -> str:
    """Strip whitespace, NFC-normalize Unicode, apply title case."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text.strip())
    # Collapse internal whitespace
    return " ".join(normalized.split()).title()


def normalize_category(raw: str) -> str:
    """Map a Vietnamese category name to a standardized English category.

    Tries exact match first, then case-insensitive prefix match.
    Logs unmapped categories so they can be added to categories.py.
    """
    if not raw:
        return "Other"
    stripped = raw.strip()

    # Exact match
    if stripped in CATEGORY_MAP:
        return CATEGORY_MAP[stripped]

    # Case-insensitive exact match
    lower = stripped.lower()
    for key, val in CATEGORY_MAP.items():
        if key.lower() == lower:
            return val

    # Prefix match (e.g. "Thịt bò" → "Thịt")
    for key, val in CATEGORY_MAP.items():
        if lower.startswith(key.lower()):
            return val

    logger.warning("Unmapped category: '%s' — add to categories.py", stripped)
    return stripped  # Return as-is so data is not lost


def validate_macros(entry: FoodEntry) -> list[str]:
    """Return list of validation warnings for an entry's macro values."""
    return entry.validate()


def dedup_key(entry: FoodEntry) -> str:
    """Generate a deduplication key as '{source}:{normalized_name_vi}'."""
    normalized = normalize_vi_name(entry.name_vi) if entry.name_vi else entry.name
    return f"{entry.source}:{normalized}"
