"""
Food reference repository — CRUD for canonical food catalog.
Replaces barcode_product_repository with extended functionality.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from src.infra.database.config import SessionLocal
from src.infra.database.models.food_reference_model import FoodReferenceModel
from src.infra.database.models.food_reference_nutrient import FoodReferenceNutrientModel
from src.infra.database.models.food_reference_serving_size import (
    FoodReferenceServingSizeModel,
)

logger = logging.getLogger(__name__)

_FOOD_REFERENCE_LOAD_OPTIONS = (
    selectinload(FoodReferenceModel.serving_size_rows),
    selectinload(FoodReferenceModel.nutrient_rows),
)


class FoodReferenceRepository:
    """Repository for food reference CRUD operations."""

    def get_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        """Get food reference entry by barcode."""
        session: Session = SessionLocal()
        try:
            stmt = (
                select(FoodReferenceModel)
                .where(FoodReferenceModel.barcode == barcode)
                .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
            )
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching barcode {barcode}: {e}")
            return None
        finally:
            session.close()

    def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        """Get food reference by ID."""
        session: Session = SessionLocal()
        try:
            stmt = (
                select(FoodReferenceModel)
                .where(FoodReferenceModel.id == ref_id)
                .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
            )
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching food_reference {ref_id}: {e}")
            return None
        finally:
            session.close()

    def get_by_fdc_id(self, fdc_id: int) -> dict[str, Any] | None:
        """Get food reference by USDA FDC ID."""
        session: Session = SessionLocal()
        try:
            stmt = (
                select(FoodReferenceModel)
                .where(FoodReferenceModel.fdc_id == fdc_id)
                .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
            )
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching fdc_id {fdc_id}: {e}")
            return None
        finally:
            session.close()

    def search_by_name(
        self, query: str, region: str = "global", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search food references by name."""
        session: Session = SessionLocal()
        try:
            stmt = (
                select(FoodReferenceModel)
                .where(FoodReferenceModel.name.ilike(f"%{query}%"))
                .where(FoodReferenceModel.region.in_([region, "global"]))
                .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
                .limit(limit)
            )
            results = session.execute(stmt).scalars().all()
            return [self._to_dict(r) for r in results]
        except Exception as e:
            logger.error(f"Error searching food_reference '{query}': {e}")
            return []
        finally:
            session.close()

    def upsert(self, data: dict[str, Any]) -> None:
        """Insert or update food reference entry (upsert by barcode)."""
        session: Session = SessionLocal()
        try:
            values = {
                "barcode": data.get("barcode"),
                "name": data.get("name"),
                "name_vi": data.get("name_vi"),
                "brand": data.get("brand"),
                "protein_100g": data.get("protein_100g"),
                "carbs_100g": data.get("carbs_100g"),
                "fat_100g": data.get("fat_100g"),
                "fiber_100g": data.get("fiber_100g", 0),
                "sugar_100g": data.get("sugar_100g", 0),
                "serving_size": data.get("serving_size"),
                "serving_sizes": data.get("serving_sizes"),
                "image_url": data.get("image_url"),
                "source": data.get("source", "fatsecret"),
                "fdc_id": data.get("fdc_id"),
                "category": data.get("category"),
                "region": data.get("region", "global"),
                "density": data.get("density", 1.0),
                "extra_nutrients": data.get("extra_nutrients"),
            }
            stmt = pg_insert(FoodReferenceModel).values(**values)
            update_fields = {k: v for k, v in values.items() if k != "barcode"}
            stmt = stmt.on_conflict_do_update(
                index_elements=[FoodReferenceModel.barcode],
                set_=update_fields,
            )
            session.execute(stmt)
            session.commit()
            refreshed = self._find_after_upsert(session, values)
            if refreshed:
                self._sync_normalized_children(session, refreshed, data)
                session.commit()
        except Exception as e:
            logger.error(f"Error upserting food_reference {data.get('barcode')}: {e}")
            session.rollback()
        finally:
            session.close()

    # Columns safe to set via upsert_seed (excludes SQLAlchemy internals)
    _SEED_COLUMNS = {
        "barcode",
        "name",
        "name_vi",
        "brand",
        "category",
        "region",
        "fdc_id",
        "protein_100g",
        "carbs_100g",
        "fat_100g",
        "fiber_100g",
        "sugar_100g",
        "extra_nutrients",
        "serving_sizes",
        "density",
        "serving_size",
        "source",
        "is_verified",
        "image_url",
    }

    def upsert_seed(self, data: dict[str, Any]) -> str:
        """Upsert a seed food entry. Returns 'inserted', 'updated', or 'skipped'."""
        session: Session = SessionLocal()
        try:
            if data.get("barcode"):
                existing = (
                    session.execute(
                        select(FoodReferenceModel)
                        .where(FoodReferenceModel.barcode == data["barcode"])
                        .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
                    )
                    .scalars()
                    .first()
                )
            else:
                existing = (
                    session.execute(
                        select(FoodReferenceModel)
                        .where(
                            FoodReferenceModel.name_vi == data.get("name_vi"),
                            FoodReferenceModel.source == data.get("source"),
                            FoodReferenceModel.region == data.get("region", "VN"),
                        )
                        .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
                    )
                    .scalars()
                    .first()
                )

            safe_data = {k: v for k, v in data.items() if k in self._SEED_COLUMNS}
            # Exclude None barcode — DB may reject NULL on unique column
            if safe_data.get("barcode") is None:
                safe_data.pop("barcode", None)
            # Truncate category to fit VARCHAR(100)
            if safe_data.get("category") and len(safe_data["category"]) > 100:
                safe_data["category"] = safe_data["category"][:100]

            if existing:
                for key, val in safe_data.items():
                    setattr(existing, key, val)
                self._sync_normalized_children(session, existing, data)
                session.commit()
                return "updated"
            else:
                entry = FoodReferenceModel(**safe_data)
                session.add(entry)
                session.flush()
                self._sync_normalized_children(session, entry, data)
                session.commit()
                return "inserted"
        except Exception as e:
            logger.error(
                f"Error upserting seed '{data.get('name_vi', data.get('name'))}': {e}"
            )
            session.rollback()
            return "skipped"
        finally:
            session.close()

    def find_batch_by_normalized_names(
        self, names_normalized: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Batch lookup by normalized ingredient names.

        Returns dict keyed by name_normalized for O(1) lookup.
        Missing names are simply absent from the result.
        """
        if not names_normalized:
            return {}

        session: Session = SessionLocal()
        try:
            stmt = (
                select(FoodReferenceModel)
                .where(FoodReferenceModel.name_normalized.in_(names_normalized))
                .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
            )
            results = session.execute(stmt).scalars().all()
            return {
                r.name_normalized: self._to_dict(r)
                for r in results
                if r.name_normalized is not None
            }
        except Exception as e:
            logger.error(f"Error batch lookup for {len(names_normalized)} names: {e}")
            return {}
        finally:
            session.close()

    def find_by_normalized_name(self, name_normalized: str) -> dict[str, Any] | None:
        """Exact-match lookup by normalized ingredient name."""
        session: Session = SessionLocal()
        try:
            stmt = (
                select(FoodReferenceModel)
                .where(FoodReferenceModel.name_normalized == name_normalized)
                .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
            )
            # .first() instead of scalar_one_or_none() — defensive against
            # hypothetical duplicates that exist before the unique constraint was added.
            result = session.execute(stmt).scalars().first()
            return self._to_dict(result) if result else None
        except Exception as e:
            logger.error(
                f"Error finding food by normalized name '{name_normalized}': {e}"
            )
            return None
        finally:
            session.close()

    def upsert_by_normalized_name(
        self,
        name: str,
        name_normalized: str,
        protein_100g: float,
        carbs_100g: float,
        fat_100g: float,
        fiber_100g: float,
        sugar_100g: float,
        source: str,
        is_verified: bool,
        external_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Insert or update food_reference matched on name_normalized.

        Preservation rule: if an existing entry has is_verified=True and
        incoming is_verified=False, the existing entry is returned unchanged
        to protect curated data from being overwritten by automated lookups.

        Uses a select-then-atomic-upsert pattern:
        1. SELECT to check is_verified protection (cannot be expressed in SQL alone).
        2. If not protected, issue INSERT ... ON DUPLICATE KEY UPDATE for atomicity
           (race-safe on the unique index added by migration 046).
        """
        session: Session = SessionLocal()
        try:
            # Step 1: check is_verified protection
            existing = (
                session.execute(
                    select(FoodReferenceModel)
                    .where(FoodReferenceModel.name_normalized == name_normalized)
                    .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
                )
                .scalars()
                .first()
            )

            if existing is not None and existing.is_verified and not is_verified:
                # Preserve curated entry — never overwrite with unverified data
                return self._to_dict(existing)

            # Step 2: atomic upsert — INSERT ... ON DUPLICATE KEY UPDATE
            values = {
                "name": name,
                "name_normalized": name_normalized,
                "protein_100g": protein_100g,
                "carbs_100g": carbs_100g,
                "fat_100g": fat_100g,
                "fiber_100g": fiber_100g,
                "sugar_100g": sugar_100g,
                "source": source,
                "is_verified": is_verified,
                "region": "global",
            }
            update_fields = {k: v for k, v in values.items() if k != "name_normalized"}
            stmt = pg_insert(FoodReferenceModel).values(**values)
            on_conflict_kwargs: dict[str, Any] = {
                "index_elements": ["name_normalized"],
                "set_": update_fields,
            }
            if not is_verified:
                # Atomically refuse to overwrite a curated (verified) row with
                # unverified data — closes the race the SELECT above leaves open
                # if a concurrent writer verifies the row between the two steps.
                on_conflict_kwargs["where"] = FoodReferenceModel.is_verified.is_(False)
            stmt = stmt.on_conflict_do_update(**on_conflict_kwargs)
            session.execute(stmt)
            session.commit()

            # Re-fetch to return the authoritative persisted row
            refreshed = (
                session.execute(
                    select(FoodReferenceModel)
                    .where(FoodReferenceModel.name_normalized == name_normalized)
                    .options(*_FOOD_REFERENCE_LOAD_OPTIONS)
                )
                .scalars()
                .first()
            )
            return self._to_dict(refreshed) if refreshed else None
        except Exception as e:
            logger.error(
                f"Error upserting food_reference by normalized name '{name_normalized}': {e}"
            )
            session.rollback()
            return None
        finally:
            session.close()

    @staticmethod
    def _to_dict(model: FoodReferenceModel) -> dict[str, Any]:
        """Convert model to dict."""
        return {
            "id": model.id,
            "barcode": model.barcode,
            "name": model.name,
            "name_vi": model.name_vi,
            "brand": model.brand,
            "category": model.category,
            "region": model.region,
            "fdc_id": model.fdc_id,
            "protein_100g": model.protein_100g,
            "carbs_100g": model.carbs_100g,
            "fat_100g": model.fat_100g,
            "fiber_100g": model.fiber_100g,
            "sugar_100g": model.sugar_100g,
            "serving_sizes": FoodReferenceRepository._serving_sizes_to_dict(model),
            "density": model.density,
            "serving_size": model.serving_size,
            "extra_nutrients": FoodReferenceRepository._nutrients_to_dict(model),
            "source": model.source,
            "is_verified": model.is_verified,
            "image_url": model.image_url,
        }

    @staticmethod
    def _find_after_upsert(
        session: Session,
        values: dict[str, Any],
    ) -> FoodReferenceModel | None:
        if values.get("barcode"):
            stmt = select(FoodReferenceModel).where(
                FoodReferenceModel.barcode == values["barcode"]
            )
        elif values.get("fdc_id"):
            stmt = select(FoodReferenceModel).where(
                FoodReferenceModel.fdc_id == values["fdc_id"]
            )
        else:
            return None
        return (
            session.execute(stmt.options(*_FOOD_REFERENCE_LOAD_OPTIONS))
            .scalars()
            .first()
        )

    @staticmethod
    def _sync_normalized_children(
        session: Session,
        model: FoodReferenceModel,
        data: dict[str, Any],
    ) -> None:
        serving_sizes = data.get("serving_sizes")
        extra_nutrients = data.get("extra_nutrients")
        if serving_sizes is not None:
            model.serving_size_rows = FoodReferenceRepository._build_serving_rows(
                serving_sizes
            )
        if extra_nutrients is not None:
            model.nutrient_rows = FoodReferenceRepository._build_nutrient_rows(
                extra_nutrients
            )
        session.flush()

    @staticmethod
    def _build_serving_rows(raw: Any) -> list[FoodReferenceServingSizeModel]:
        if not isinstance(raw, list):
            return []
        rows: list[FoodReferenceServingSizeModel] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("label") or "").strip()
            if not name:
                continue
            rows.append(
                FoodReferenceServingSizeModel(
                    name=name[:100],
                    grams=FoodReferenceRepository._as_float(item.get("grams")),
                    milliliters=FoodReferenceRepository._as_float(
                        item.get("milliliters") or item.get("ml")
                    ),
                    is_default=bool(item.get("is_default", idx == 0)),
                    position=idx,
                )
            )
        return rows

    @staticmethod
    def _build_nutrient_rows(raw: Any) -> list[FoodReferenceNutrientModel]:
        if not isinstance(raw, dict):
            return []
        rows: list[FoodReferenceNutrientModel] = []
        for key, value in sorted(raw.items()):
            if isinstance(value, dict):
                amount = FoodReferenceRepository._as_float(value.get("amount"))
                unit = value.get("unit")
            else:
                amount = FoodReferenceRepository._as_float(value)
                unit = None
            if amount is None:
                continue
            rows.append(
                FoodReferenceNutrientModel(
                    nutrient_key=str(key)[:100],
                    amount=amount,
                    unit=str(unit)[:32] if unit else None,
                )
            )
        return rows

    @staticmethod
    def _serving_sizes_to_dict(model: FoodReferenceModel) -> Any:
        rows = getattr(model, "serving_size_rows", None)
        if not rows:
            return model.serving_sizes
        return [
            {
                "name": row.name,
                "grams": row.grams,
                "milliliters": row.milliliters,
                "is_default": row.is_default,
            }
            for row in rows
        ]

    @staticmethod
    def _nutrients_to_dict(model: FoodReferenceModel) -> Any:
        rows = getattr(model, "nutrient_rows", None)
        if not rows:
            return model.extra_nutrients
        raw = model.extra_nutrients if isinstance(model.extra_nutrients, dict) else {}
        projected = dict(raw)
        for row in rows:
            legacy_value = raw.get(row.nutrient_key)
            if isinstance(legacy_value, dict):
                projected[row.nutrient_key] = {
                    **legacy_value,
                    "amount": row.amount,
                    "unit": row.unit,
                }
            elif row.nutrient_key in raw:
                projected[row.nutrient_key] = row.amount
            else:
                projected[row.nutrient_key] = {
                    "amount": row.amount,
                    "unit": row.unit,
                }
        return projected

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
