"""Decide when parse-text should expand a dish versus keep listed foods."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

ParseTextInputKind = Literal["dish", "ingredient_list", "single_food"]

_LIST_SPLIT = re.compile(
    r"\s*(?:,|;|/|\n|\+| and | và | with | với | plus )\s*",
    re.IGNORECASE,
)
_MASS_VOLUME = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:g|gram|grams|kg|ml|l|oz|lb)s?\b",
    re.IGNORECASE,
)
_QUANTITY_UNIT = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*[A-Za-zÀ-ỹ%]+\b",
    re.IGNORECASE,
)
_DISH_MARKERS = frozenset(
    {
        "bowl",
        "bun",
        "bún",
        "burger",
        "com",
        "cơm",
        "curry",
        "dish",
        "meal",
        "mi",
        "mì",
        "noodle",
        "pasta",
        "pho",
        "phở",
        "pizza",
        "platter",
        "ramen",
        "salad",
        "sandwich",
        "soup",
        "stew",
        "taco",
        "wrap",
    }
)
_DISH_UNITS = frozenset({"bát", "bowl", "ổ", "plate", "tô", "đĩa"})
_STOP_TOKENS = frozenset(
    {
        "a",
        "an",
        "of",
        "one",
        "the",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
    }
)


def classify_parse_text_input(text: str) -> ParseTextInputKind:
    """Classify a parse-text utterance as a dish, listed foods, or one measured food."""
    compact = " ".join(text.strip().split())
    if not compact:
        return "single_food"
    parts = [part for part in _LIST_SPLIT.split(compact) if part.strip()]
    if len(parts) >= 2:
        return "ingredient_list"
    if len(_QUANTITY_UNIT.findall(compact)) >= 2:
        return "ingredient_list"
    if _MASS_VOLUME.search(compact):
        return "single_food"
    if _looks_like_named_dish(compact):
        return "dish"
    return "single_food"


def composition_retry_feedback(
    text: str, items: list[dict[str, Any]]
) -> str | None:
    """Ask the model to expand a named dish returned as a single row."""
    if classify_parse_text_input(text) != "dish":
        return None
    if len(items) != 1:
        return None
    return (
        "The user named a prepared dish. Return the edible components of one "
        "serving, not the dish as a single row. Do not recurse into recipes."
    )


def _looks_like_named_dish(text: str) -> bool:
    tokens = _tokens(text)
    if tokens & _DISH_MARKERS or tokens & _DISH_UNITS:
        return True
    if re.match(r"^\d", text.strip()):
        return False
    return len(tokens - _STOP_TOKENS) >= 3


def _tokens(text: str) -> set[str]:
    folded = "".join(
        char
        for char in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(char)
    )
    return set(re.findall(r"[a-z0-9]+", folded))
