import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class GenSpec:
    meal_type: str
    cuisine: str
    calorie_band: int


def _band(calories: int) -> int:
    return int(round(calories / 100.0) * 100)


class CatalogGenerationService:
    """Generate meal structure, verify macros, embed, and upsert catalog rows."""

    def __init__(
        self, *, structure_gen, macro_computer, images, embedder, repo
    ) -> None:
        self._structure_gen = structure_gen
        self._macro_computer = macro_computer
        self._images = images
        self._embedder = embedder
        self._repo = repo

    async def generate_for(self, spec: GenSpec, count: int) -> int:
        drafts = await self._structure_gen.generate(spec, count)
        created = 0
        for draft in drafts:
            macros = await self._macro_computer.compute(draft.get("ingredients", []))
            if macros is None:
                continue

            name = draft["meal_name"]
            embedding = await self._embedder.embed(self._embed_text(draft))
            if self._repo.exists_similar(name, embedding):
                continue

            image_url, thumbnail_url = await self._images.resolve(name)
            self._repo.upsert(
                {
                    "id": f"cat_{uuid.uuid4().hex}",
                    "meal_name": name,
                    "english_name": name,
                    "calories": macros.calories,
                    "protein_g": macros.protein_g,
                    "carbs_g": macros.carbs_g,
                    "fat_g": macros.fat_g,
                    "fiber_g": macros.fiber_g,
                    "calorie_band": _band(macros.calories),
                    "cuisine": draft.get("cuisine"),
                    "meal_types": draft.get("meal_types", [spec.meal_type]),
                    "ingredients": draft.get("ingredients", []),
                    "recipe_steps": None,
                    "recipe_status": "none",
                    "dietary_flags": draft.get("dietary_flags", []),
                    "allergen_flags": draft.get("allergen_flags", []),
                    "tags": draft.get("tags", []),
                    "image_url": image_url,
                    "thumbnail_url": thumbnail_url,
                    "image_status": "ready" if image_url else "pending",
                    "embedding": embedding,
                    "origin": "generated",
                    "status": "active",
                    "language": "en",
                }
            )
            created += 1
        return created

    @staticmethod
    def _embed_text(draft: dict[str, Any]) -> str:
        ingredients = ", ".join(
            ingredient.get("name", "") for ingredient in draft.get("ingredients", [])
        )
        return (
            f"{draft.get('meal_name', '')} | {draft.get('cuisine', '')} | "
            f"{ingredients} | {' '.join(draft.get('tags', []))}"
        )
