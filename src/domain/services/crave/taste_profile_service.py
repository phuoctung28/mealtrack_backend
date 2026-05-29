from dataclasses import dataclass, field

WEIGHT = {"save": 1.0, "cook": 2.0, "skip": -0.5}
LEARNING_RATE = 0.1


@dataclass
class SwipeSignal:
    direction: str
    cuisine: str | None = None
    tags: list[str] = field(default_factory=list)
    ingredients: list[str] = field(default_factory=list)


def _nudge(table: dict[str, float], key: str | None, delta: float) -> None:
    if not key:
        return
    table[key] = max(-1.0, min(1.0, table.get(key, 0.0) + LEARNING_RATE * delta))


class TasteProfileService:
    def apply(self, profile: dict, signal: SwipeSignal) -> dict:
        weight = WEIGHT.get(signal.direction, 0.0)
        cuisine = dict(profile.get("cuisine_affinity", {}))
        ingredient = dict(profile.get("ingredient_affinity", {}))
        tag = dict(profile.get("tag_affinity", {}))

        _nudge(cuisine, signal.cuisine, weight)
        for name in signal.ingredients:
            _nudge(ingredient, name, weight)
        for tag_name in signal.tags:
            _nudge(tag, tag_name, weight)

        return {
            **profile,
            "cuisine_affinity": cuisine,
            "ingredient_affinity": ingredient,
            "tag_affinity": tag,
        }

    @staticmethod
    def update_centroid(
        current: list[float] | None, meal_embedding: list[float], n_liked: int
    ) -> list[float]:
        if current is None or n_liked <= 1:
            return list(meal_embedding)
        return [
            (current_value * (n_liked - 1) + embedding_value) / n_liked
            for current_value, embedding_value in zip(
                current, meal_embedding, strict=False
            )
        ]
