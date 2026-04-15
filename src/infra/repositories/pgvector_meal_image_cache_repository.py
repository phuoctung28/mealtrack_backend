"""pgvector-backed VectorCachePort (synchronous SQLAlchemy session)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.domain.model.meal_image_cache import CachedImage, CachedImageUpsert
from src.infra.database.models.meal_image_cache import MealImageCacheModel


class PgvectorMealImageCacheRepository:
    def __init__(self, session: Session):
        self._session = session

    async def query_nearest(
        self, text_embedding: list[float]
    ) -> Optional[CachedImage]:
        # Use pgvector cosine distance operator (<=>)
        emb_literal = str(text_embedding)
        stmt = text(
            "SELECT id, meal_name, name_slug, image_url, thumbnail_url, source, "
            "confidence, text_embedding <=> CAST(:emb AS vector) AS distance "
            "FROM meal_image_cache "
            "ORDER BY distance ASC LIMIT 1"
        )
        row = self._session.execute(stmt, {"emb": emb_literal}).first()
        if row is None:
            return None
        _, meal_name, name_slug, image_url, thumbnail_url, source, confidence, distance = row
        return CachedImage(
            meal_name=meal_name,
            name_slug=name_slug,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            source=source,
            confidence=float(confidence) if confidence is not None else None,
            cosine=1.0 - float(distance),
        )

    async def upsert(self, record: CachedImageUpsert) -> None:
        emb_literal = str(record.text_embedding)
        stmt = text(
            "INSERT INTO meal_image_cache "
            "(meal_name, name_slug, text_embedding, image_url, thumbnail_url, source, confidence) "
            "VALUES (:meal_name, :name_slug, CAST(:emb AS vector), :image_url, "
            "        :thumbnail_url, :source, :confidence) "
            "ON CONFLICT (name_slug) DO UPDATE SET "
            "  text_embedding = CAST(:emb AS vector), "
            "  image_url = EXCLUDED.image_url, "
            "  thumbnail_url = EXCLUDED.thumbnail_url, "
            "  source = EXCLUDED.source, "
            "  confidence = EXCLUDED.confidence, "
            "  meal_name = EXCLUDED.meal_name"
        )
        self._session.execute(stmt, {
            "meal_name": record.meal_name,
            "name_slug": record.name_slug,
            "emb": emb_literal,
            "image_url": record.image_url,
            "thumbnail_url": record.thumbnail_url,
            "source": record.source,
            "confidence": record.confidence,
        })
        self._session.commit()
