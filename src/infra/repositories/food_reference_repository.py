"""
Food reference repository — CRUD for canonical food catalog.
Replaces barcode_product_repository with extended functionality.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.infra.database.config import SessionLocal
from src.infra.database.models.food_reference_model import FoodReferenceModel

logger = logging.getLogger(__name__)


class FoodReferenceRepository:
    """Repository for food reference CRUD operations."""

    def get_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Get food reference entry by barcode."""
        session: Session = SessionLocal()
        try:
            stmt = select(FoodReferenceModel).where(
                FoodReferenceModel.barcode == barcode
            )
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching barcode {barcode}: {e}")
            return None
        finally:
            session.close()

    def get_by_id(self, ref_id: int) -> Optional[Dict[str, Any]]:
        """Get food reference by ID."""
        session: Session = SessionLocal()
        try:
            stmt = select(FoodReferenceModel).where(FoodReferenceModel.id == ref_id)
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching food_reference {ref_id}: {e}")
            return None
        finally:
            session.close()

    def get_by_fdc_id(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        """Get food reference by USDA FDC ID."""
        session: Session = SessionLocal()
        try:
            stmt = select(FoodReferenceModel).where(FoodReferenceModel.fdc_id == fdc_id)
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching fdc_id {fdc_id}: {e}")
            return None
        finally:
            session.close()

    def search_by_name(
        self, query: str, region: str = "global", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search food references by name."""
        session: Session = SessionLocal()
        try:
            stmt = (
                select(FoodReferenceModel)
                .where(FoodReferenceModel.name.ilike(f"%{query}%"))
                .where(FoodReferenceModel.region.in_([region, "global"]))
                .limit(limit)
            )
            results = session.execute(stmt).scalars().all()
            return [self._to_dict(r) for r in results]
        except Exception as e:
            logger.error(f"Error searching food_reference '{query}': {e}")
            return []
        finally:
            session.close()

    def upsert(self, data: Dict[str, Any]) -> None:
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

    def upsert_seed(self, data: Dict[str, Any]) -> str:
        """Upsert a seed food entry. Returns 'inserted', 'updated', or 'skipped'."""
        session: Session = SessionLocal()
        try:
            if data.get("barcode"):
                existing = (
                    session.execute(
                        select(FoodReferenceModel).where(
                            FoodReferenceModel.barcode == data["barcode"]
                        )
                    )
                    .scalars()
                    .first()
                )
            else:
                existing = (
                    session.execute(
                        select(FoodReferenceModel).where(
                            FoodReferenceModel.name_vi == data.get("name_vi"),
                            FoodReferenceModel.source == data.get("source"),
                            FoodReferenceModel.region == data.get("region", "VN"),
                        )
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
                session.commit()
                return "updated"
            else:
                entry = FoodReferenceModel(**safe_data)
                session.add(entry)
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
        self, names_normalized: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Batch lookup by normalized ingredient names.

        Returns dict keyed by name_normalized for O(1) lookup.
        Missing names are simply absent from the result.
        """
        if not names_normalized:
            return {}

        session: Session = SessionLocal()
        try:
            stmt = select(FoodReferenceModel).where(
                FoodReferenceModel.name_normalized.in_(names_normalized)
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

    def find_by_normalized_name(self, name_normalized: str) -> Optional[Dict[str, Any]]:
        """Exact-match lookup by normalized ingredient name."""
        session: Session = SessionLocal()
        try:
            stmt = select(FoodReferenceModel).where(
                FoodReferenceModel.name_normalized == name_normalized
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
        external_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
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
                    select(FoodReferenceModel).where(
                        FoodReferenceModel.name_normalized == name_normalized
                    )
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
            stmt = stmt.on_conflict_do_update(
                index_elements=["name_normalized"],
                set_=update_fields,
            )
            session.execute(stmt)
            session.commit()

            # Re-fetch to return the authoritative persisted row
            refreshed = (
                session.execute(
                    select(FoodReferenceModel).where(
                        FoodReferenceModel.name_normalized == name_normalized
                    )
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
    def _to_dict(model: FoodReferenceModel) -> Dict[str, Any]:
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
            "serving_sizes": model.serving_sizes,
            "density": model.density,
            "serving_size": model.serving_size,
            "extra_nutrients": model.extra_nutrients,
            "source": model.source,
            "is_verified": model.is_verified,
            "image_url": model.image_url,
        }
