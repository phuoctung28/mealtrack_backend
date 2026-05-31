import math
from typing import Any, cast

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.infra.database.models.crave.meal_catalog_model import MealCatalog


class MealCatalogRepository:
    def __init__(self, session: Session):
        self._session = session

    def upsert(self, data: dict[str, Any]) -> MealCatalog:
        row = self._session.get(MealCatalog, data["id"])
        if row is None:
            row = MealCatalog(**data)
            self._session.add(row)
            return row
        for key, value in data.items():
            setattr(row, key, value)
        return row

    def get(self, meal_id: str) -> MealCatalog | None:
        return self._session.get(MealCatalog, meal_id)

    def fetch_candidates(
        self,
        *,
        meal_type: str,
        calorie_band: int,
        exclude_allergens: list[str],
        required_diet: list[str],
        exclude_ids: list[str],
        limit: int,
        band_tolerance: int = 100,
    ) -> list[MealCatalog]:
        conditions = [
            MealCatalog.status == "active",
            MealCatalog.calorie_band.between(
                calorie_band - band_tolerance, calorie_band + band_tolerance
            ),
        ]
        if exclude_ids:
            conditions.append(MealCatalog.id.notin_(exclude_ids))

        rows = list(
            self._session.execute(
                select(MealCatalog).where(and_(*conditions)).limit(limit)
            ).scalars()
        )

        def ok(meal: MealCatalog) -> bool:
            if meal_type not in (meal.meal_types or []):
                return False
            if any(a in (meal.allergen_flags or []) for a in exclude_allergens):
                return False
            if required_diet and not all(
                diet in (meal.dietary_flags or []) for diet in required_diet
            ):
                return False
            return True

        return [meal for meal in rows if ok(meal)]

    def fetch_by_taste(
        self,
        *,
        meal_type: str,
        calorie_band: int,
        embedding: list[float] | None,
        exclude_allergens: list[str],
        required_diet: list[str],
        exclude_ids: list[str],
        limit: int,
        band_tolerance: int = 100,
    ) -> list[MealCatalog]:
        candidates = self.fetch_candidates(
            meal_type=meal_type,
            calorie_band=calorie_band,
            exclude_allergens=exclude_allergens,
            required_diet=required_diet,
            exclude_ids=exclude_ids,
            limit=max(limit * 5, 100),
            band_tolerance=band_tolerance,
        )
        if not embedding:
            return candidates[:limit]

        def cosine_distance(meal: MealCatalog) -> float:
            if not meal.embedding:
                return 1.0
            meal_embedding = cast(list[float], meal.embedding)
            dot = sum(a * b for a, b in zip(embedding, meal_embedding, strict=False))
            norm_a = math.sqrt(sum(a * a for a in embedding))
            norm_b = math.sqrt(sum(b * b for b in meal_embedding))
            if norm_a == 0 or norm_b == 0:
                return 1.0
            return 1.0 - dot / (norm_a * norm_b)

        candidates.sort(key=cosine_distance)
        return candidates[:limit]

    def increment_stats(
        self,
        meal_id: str,
        *,
        shown: int = 0,
        saved: int = 0,
        cooked: int = 0,
        skipped: int = 0,
    ) -> None:
        meal = self.get(meal_id)
        if meal is None:
            return
        meal_record = cast(Any, meal)
        meal_record.times_shown = (meal.times_shown or 0) + shown
        meal_record.times_saved = (meal.times_saved or 0) + saved
        meal_record.times_cooked = (meal.times_cooked or 0) + cooked
        meal_record.times_skipped = (meal.times_skipped or 0) + skipped

    def save_recipe(self, meal_id: str, steps: list[str]) -> None:
        meal = self.get(meal_id)
        if meal is not None:
            meal_record = cast(Any, meal)
            meal_record.recipe_steps = steps
            meal_record.recipe_status = "ready"

    def exists_similar(self, name: str, embedding: list[float] | None) -> bool:
        stmt = (
            select(func.count())
            .select_from(MealCatalog)
            .where(func.lower(MealCatalog.meal_name) == name.lower())
        )
        return int(self._session.execute(stmt).scalar() or 0) > 0

    def count_by_cell(self) -> dict[tuple[str, str, int], int]:
        rows = self._session.execute(
            select(
                MealCatalog.cuisine, MealCatalog.calorie_band, MealCatalog.meal_types
            ).where(MealCatalog.status == "active")
        )
        counts: dict[tuple[str, str, int], int] = {}
        for cuisine, band, meal_types in rows:
            for meal_type in meal_types or []:
                key = (meal_type, cuisine or "", band)
                counts[key] = counts.get(key, 0) + 1
        return counts
