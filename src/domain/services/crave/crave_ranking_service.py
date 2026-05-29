import math
from dataclasses import dataclass, field
from typing import Any

WEIGHTS = {
    "budget": 0.35,
    "taste": 0.30,
    "macro": 0.15,
    "novelty": 0.15,
    "on_hand": 0.05,
}


@dataclass
class RankInputs:
    target_calories: int
    cuisine_affinity: dict[str, float] = field(default_factory=dict)
    ingredient_affinity: dict[str, float] = field(default_factory=dict)
    tag_affinity: dict[str, float] = field(default_factory=dict)
    taste_cosine: dict[str, float] = field(default_factory=dict)
    seen_ids: set[str] = field(default_factory=set)


@dataclass
class RankedMeal:
    meal: Any
    match: int
    reason: str


def _budget_fit(meal_calories: int, target: int) -> float:
    if target <= 0:
        return 0.5
    sigma = max(target * 0.2, 60)
    return math.exp(-((meal_calories - target) ** 2) / (2 * sigma**2))


class CraveRankingService:
    def rank(self, meals: list[Any], inputs: RankInputs) -> list[RankedMeal]:
        ranked = []
        for meal in meals:
            budget = _budget_fit(meal.calories, inputs.target_calories)
            taste = max(
                inputs.taste_cosine.get(meal.id, 0.0),
                inputs.cuisine_affinity.get(getattr(meal, "cuisine", "") or "", 0.0),
            )
            tag = max(
                (
                    inputs.tag_affinity.get(tag_name, 0.0)
                    for tag_name in (getattr(meal, "tags", []) or [])
                ),
                default=0.0,
            )
            macro = 0.5
            novelty = 0.0 if meal.id in inputs.seen_ids else 1.0
            on_hand = 0.0
            score = (
                WEIGHTS["budget"] * budget
                + WEIGHTS["taste"] * max(taste, tag)
                + WEIGHTS["macro"] * macro
                + WEIGHTS["novelty"] * novelty
                + WEIGHTS["on_hand"] * on_hand
            )
            seen_penalty = 0.15 if meal.id in inputs.seen_ids else 0.0
            match = max(0, min(100, round((score - seen_penalty) * 100)))
            ranked.append(
                RankedMeal(
                    meal=meal,
                    match=match,
                    reason=self._reason(meal, budget, taste, inputs),
                )
            )

        ranked.sort(key=lambda item: item.match, reverse=True)
        return ranked

    @staticmethod
    def _reason(meal: Any, budget: float, taste: float, inputs: RankInputs) -> str:
        contributions = {
            "taste": WEIGHTS["taste"] * taste,
            "budget": WEIGHTS["budget"] * budget,
        }
        if max(
            contributions, key=lambda key: contributions[key]
        ) == "taste" and getattr(meal, "cuisine", None):
            return f"Because you love {meal.cuisine}"
        return f"Fits your {inputs.target_calories} kcal target"
