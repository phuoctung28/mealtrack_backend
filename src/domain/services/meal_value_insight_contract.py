"""Validated meal value insight payload helpers."""

from dataclasses import dataclass, field
from typing import Any

_TEXT_LABEL_PREFIXES = (
    "benefit",
    "balance",
    "balanced",
    "caution",
    "warning",
    "warn",
)


@dataclass(frozen=True)
class ValueInsight:
    """Short insight text and UI category."""

    text: str
    category: str
    highlights: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IngredientValueInsight:
    """Short ingredient insight."""

    ingredient_name: str
    text: str
    category: str
    highlights: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MealValueInsights:
    """Meal detail insight payload."""

    meal_bullets: list[ValueInsight]
    ingredient_insights: list[IngredientValueInsight]


def parse_ai_result(result: Any) -> MealValueInsights | None:
    if not isinstance(result, dict):
        return None
    meal_bullets = [
        item
        for raw in result.get("meal_bullets", [])[:2]
        if (item := _parse_value_insight(raw))
    ]
    ingredient_insights = [
        item
        for raw in result.get("ingredient_insights", [])[:2]
        if (item := _parse_ingredient_insight(raw))
    ]
    if not meal_bullets and not ingredient_insights:
        return None
    return MealValueInsights(
        meal_bullets=meal_bullets,
        ingredient_insights=ingredient_insights,
    )


def serialize_insights(insights: MealValueInsights) -> dict[str, list[dict[str, Any]]]:
    return {
        "meal_bullets": [
            {
                "text": item.text,
                "category": item.category,
                "highlights": item.highlights,
            }
            for item in insights.meal_bullets
        ],
        "ingredient_insights": [
            {
                "ingredient_name": item.ingredient_name,
                "text": item.text,
                "category": item.category,
                "highlights": item.highlights,
            }
            for item in insights.ingredient_insights
        ],
    }


def _parse_value_insight(raw: Any) -> ValueInsight | None:
    if not isinstance(raw, dict):
        return None
    text = _bounded_text(raw.get("text"))
    category = _category(raw.get("category"))
    highlights = _highlights(raw, text)
    if not text or len(highlights) != 1:
        return None
    return ValueInsight(text=text, category=category, highlights=highlights)


def _parse_ingredient_insight(raw: Any) -> IngredientValueInsight | None:
    if not isinstance(raw, dict):
        return None
    name = _bounded_text(raw.get("ingredient_name"), max_length=60)
    text = _bounded_text(raw.get("text"))
    category = _category(raw.get("category"))
    highlights = _highlights(raw, text)
    if not name or not text or len(highlights) != 1:
        return None
    return IngredientValueInsight(
        ingredient_name=name,
        text=text,
        category=category,
        highlights=highlights,
    )


def _bounded_text(value: Any, max_length: int = 120) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.strip().split())
    text = _strip_text_label(text)
    return text[:max_length].rstrip()


def _category(value: Any) -> str:
    if value in {"benefit", "caution", "balance"}:
        return str(value)
    return "balance"


def _strip_text_label(text: str) -> str:
    label, separator, rest = text.partition(":")
    if separator and label.strip().casefold() in _TEXT_LABEL_PREFIXES:
        return rest.strip()
    return text


def _highlights(raw: dict[str, Any], text: str) -> list[str]:
    values = raw.get("highlights")
    if not isinstance(values, list):
        values = [raw.get("highlight")]

    highlights: list[str] = []
    for value in values:
        highlight = _bounded_text(value, max_length=40)
        if not highlight:
            continue
        if highlight.casefold() not in text.casefold():
            continue
        if highlight.casefold() in {item.casefold() for item in highlights}:
            continue
        highlights.append(highlight)
        if len(highlights) == 1:
            break
    return highlights
