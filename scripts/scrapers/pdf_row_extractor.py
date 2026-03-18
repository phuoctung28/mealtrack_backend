"""
Internal helpers for VN FCT PDF row extraction.
Handles column detection, value parsing, and row classification.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Regex patterns
_FOOTNOTE_RE = re.compile(r"^\s*[\*\†\#\(]")
_NUMBER_RE = re.compile(r"^\s*-?\d+[\.,]?\d*\s*$")
_BLANK_RE = re.compile(r"^\s*[-–—tr\.]+\s*$")  # Trace or dash = 0

# Known column header fragments (Vietnamese + common abbreviations)
_HEADER_KEYWORDS = {
    "tên", "protein", "lipit", "glucid", "chất xơ", "tro",
    "năng lượng", "nước", "food", "name", "water", "energy",
    "ca", "fe", "vit", "caroten", "edible", "portion",
    "mg", "mcg", "kcal", "kj", "g/100", "số tt",
}

# Columns we care about (position-based fallback mapping)
# VN FCT 2007 standard column order (0-indexed):
# 0: serial no, 1: name_vi, 2: name_en, 3: water%, 4: energy_kcal,
# 5: protein, 6: fat, 7: carbs, 8: fiber, 9: ash,
# 10: Ca_mg, 11: Fe_mg, 12: beta_carotene_mcg, 13: vit_c_mg
STANDARD_COL_PROTEIN = 5
STANDARD_COL_FAT = 6
STANDARD_COL_CARBS = 7
STANDARD_COL_FIBER = 8
STANDARD_COL_CA = 10
STANDARD_COL_FE = 11
STANDARD_COL_VIT_A = 12
STANDARD_COL_VIT_C = 13


def is_header_row(cells: list[Optional[str]]) -> bool:
    """Return True if this row looks like a column header row."""
    text = " ".join((c or "").lower() for c in cells if c)
    matches = sum(1 for kw in _HEADER_KEYWORDS if kw in text)
    return matches >= 2


def is_footnote_row(cells: list[Optional[str]]) -> bool:
    """Return True if this row is a footnote/note row to skip."""
    first = next((c for c in cells if c and c.strip()), "")
    return bool(_FOOTNOTE_RE.match(first))


def is_food_group_header(cells: list[Optional[str]]) -> Optional[str]:
    """
    Return the food group name if this is a group header row, else None.
    Group headers span the full row as a single non-numeric text cell.
    """
    non_empty = [c.strip() for c in cells if c and c.strip()]
    if len(non_empty) != 1:
        return None
    text = non_empty[0]
    # Must be text, not a number or a footnote
    if _NUMBER_RE.match(text) or _FOOTNOTE_RE.match(text):
        return None
    # Short enough for a category label, not a food name (food names tend to be longer)
    if len(text) > 80:
        return None
    return text


def parse_float(raw: Optional[str]) -> float:
    """Parse a cell value to float; return 0.0 for dashes/blanks/None."""
    if not raw:
        return 0.0
    stripped = raw.strip()
    if not stripped or _BLANK_RE.match(stripped):
        return 0.0
    # Replace comma decimals (e.g. "3,5" → "3.5")
    cleaned = stripped.replace(",", ".").replace(" ", "")
    try:
        value = float(cleaned)
        return max(0.0, value)  # clamp negatives to 0
    except ValueError:
        logger.debug("Cannot parse float from '%s'", raw)
        return 0.0


def extract_names(cells: list[Optional[str]]) -> tuple[str, str]:
    """
    Extract (name_vi, name_en) from a row.
    Assumes cell[1] = name_vi, cell[2] = name_en (VN FCT standard layout).
    Falls back to cell[0] if cell[1] is empty.
    """
    def get(idx: int) -> str:
        if idx < len(cells):
            return (cells[idx] or "").strip()
        return ""

    name_vi = get(1) or get(0)
    name_en = get(2)

    # If name_en looks like a number or is empty, treat as absent
    if _NUMBER_RE.match(name_en) if name_en else True:
        name_en = ""

    return name_vi, name_en


def extract_macros_and_micros(
    cells: list[Optional[str]],
) -> dict[str, float]:
    """Extract macro + micronutrient values using standard column positions."""
    return {
        "protein_100g": parse_float(cells[STANDARD_COL_PROTEIN] if STANDARD_COL_PROTEIN < len(cells) else None),
        "fat_100g": parse_float(cells[STANDARD_COL_FAT] if STANDARD_COL_FAT < len(cells) else None),
        "carbs_100g": parse_float(cells[STANDARD_COL_CARBS] if STANDARD_COL_CARBS < len(cells) else None),
        "fiber_100g": parse_float(cells[STANDARD_COL_FIBER] if STANDARD_COL_FIBER < len(cells) else None),
        "calcium_mg": parse_float(cells[STANDARD_COL_CA] if STANDARD_COL_CA < len(cells) else None),
        "iron_mg": parse_float(cells[STANDARD_COL_FE] if STANDARD_COL_FE < len(cells) else None),
        "vitamin_a_mcg": parse_float(cells[STANDARD_COL_VIT_A] if STANDARD_COL_VIT_A < len(cells) else None),
        "vitamin_c_mg": parse_float(cells[STANDARD_COL_VIT_C] if STANDARD_COL_VIT_C < len(cells) else None),
    }
