"""Canonicalize meal names into a stable, ASCII-only, lowercase slug."""

from __future__ import annotations

import re
import unicodedata


def slug(name: str) -> str:
    """
    - Strip, lowercase
    - Unicode NFKD → ASCII (drop diacritics: 'ơ' → 'o')
    - Collapse non-alphanumerics to single '-'
    - Strip leading/trailing '-'
    - Raise ValueError if empty
    """
    if not name or not name.strip():
        raise ValueError("meal name must be non-empty")

    normalized = unicodedata.normalize("NFKD", name.strip().lower())
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")

    if not collapsed:
        raise ValueError(f"meal name {name!r} produced empty slug")

    return collapsed
