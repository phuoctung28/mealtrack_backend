"""
Barcode product repository for caching barcode API responses.
"""

from typing import Optional, Dict, Any
import logging

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from src.infra.database.config import SessionLocal
from src.infra.database.models.barcode_product_model import BarcodeProductModel

logger = logging.getLogger(__name__)


class BarcodeProductRepository:
    """Repository for barcode product cache operations."""

    def get_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Get barcode product from cache by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Product dict or None if not found
        """
        session: Session = SessionLocal()
        try:
            stmt = select(BarcodeProductModel).where(
                BarcodeProductModel.barcode == barcode
            )
            result = session.execute(stmt).scalar_one_or_none()

            if not result:
                return None

            return {
                "name": result.name,
                "brand": result.brand,
                "barcode": result.barcode,
                "calories_100g": result.calories_100g,
                "protein_100g": result.protein_100g,
                "carbs_100g": result.carbs_100g,
                "fat_100g": result.fat_100g,
                "serving_size": result.serving_size,
                "image_url": result.image_url,
                "source": result.source,
            }
        except Exception as e:
            logger.error(f"Error fetching barcode {barcode}: {e}")
            return None
        finally:
            session.close()

    def save(self, data: Dict[str, Any]) -> None:
        """
        Save or update barcode product in cache (upsert).

        Args:
            data: Product data dict with all fields
        """
        session: Session = SessionLocal()
        try:
            stmt = mysql_insert(BarcodeProductModel).values(
                barcode=data.get("barcode"),
                name=data.get("name"),
                brand=data.get("brand"),
                calories_100g=data.get("calories_100g"),
                protein_100g=data.get("protein_100g"),
                carbs_100g=data.get("carbs_100g"),
                fat_100g=data.get("fat_100g"),
                serving_size=data.get("serving_size"),
                image_url=data.get("image_url"),
                source=data.get("source", "unknown"),
            )

            # On conflict, update all fields except barcode
            stmt = stmt.on_duplicate_key_update(
                name=data.get("name"),
                brand=data.get("brand"),
                calories_100g=data.get("calories_100g"),
                protein_100g=data.get("protein_100g"),
                carbs_100g=data.get("carbs_100g"),
                fat_100g=data.get("fat_100g"),
                serving_size=data.get("serving_size"),
                image_url=data.get("image_url"),
                source=data.get("source", "unknown"),
            )

            session.execute(stmt)
            session.commit()
        except Exception as e:
            logger.error(f"Error saving barcode {data.get('barcode')}: {e}")
            session.rollback()
        finally:
            session.close()
