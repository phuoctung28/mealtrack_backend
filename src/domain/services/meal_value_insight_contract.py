"""Validated meal value insight payload helpers."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValueInsight:
    """Short insight text and UI category."""

    text: str
    category: str


@dataclass(frozen=True)
class IngredientValueInsight:
    """Short ingredient insight."""

    ingredient_name: str
    text: str
    category: str


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


def serialize_insights(insights: MealValueInsights) -> dict[str, list[dict[str, str]]]:
    return {
        "meal_bullets": [
            {"text": item.text, "category": item.category}
            for item in insights.meal_bullets
        ],
        "ingredient_insights": [
            {
                "ingredient_name": item.ingredient_name,
                "text": item.text,
                "category": item.category,
            }
            for item in insights.ingredient_insights
        ],
    }


def _parse_value_insight(raw: Any) -> ValueInsight | None:
    if not isinstance(raw, dict):
        return None
    text = _bounded_text(raw.get("text"))
    category = _category(raw.get("category"))
    if not text:
        return None
    return ValueInsight(text=text, category=category)


def _parse_ingredient_insight(raw: Any) -> IngredientValueInsight | None:
    if not isinstance(raw, dict):
        return None
    name = _bounded_text(raw.get("ingredient_name"), max_length=60)
    text = _bounded_text(raw.get("text"))
    category = _category(raw.get("category"))
    if not name or not text:
        return None
    return IngredientValueInsight(
        ingredient_name=name,
        text=text,
        category=category,
    )


def _bounded_text(value: Any, max_length: int = 120) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.strip().split())
    return text[:max_length].rstrip()


def _category(value: Any) -> str:
    if value in {"benefit", "caution", "balance"}:
        return str(value)
    return "balance"
