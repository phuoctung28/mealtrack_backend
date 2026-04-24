"""pgvector-backed VectorCachePort (synchronous SQLAlchemy session)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.domain.model.meal_image_cache import CachedImage, CachedImageUpsert


class PgvectorMealImageCacheRepository:
    # NOTE: Uses synchronous SQLAlchemy session wrapped in async def.
    # This blocks the event loop during DB calls. Consider migrating to
    # asyncio.to_thread() or AsyncSession when addressing performance.

    def __init__(self, session: Session):
        self._session = session

    async def query_nearest(self, text_embedding: list[float]) -> Optional[CachedImage]:
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
        (
            _,
            meal_name,
            name_slug,
            image_url,
            thumbnail_url,
            source,
            confidence,
            distance,
        ) = row
        return CachedImage(
            meal_name=meal_name,
            name_slug=name_slug,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            source=source,
            confidence=float(confidence) if confidence is not None else None,
            cosine=1.0 - float(distance),
        )

    async def query_nearest_batch(
        self, text_embeddings: list[list[float]]
    ) -> list[Optional[CachedImage]]:
        """Batch ANN query — single SQL with UNNEST for all embeddings."""
        if not text_embeddings:
            return []

        # Convert embeddings to PostgreSQL array format for UNNEST.
        # Using bound parameter :emb_array avoids f-string SQL interpolation.
        emb_strs = [str(emb) for emb in text_embeddings]

        stmt = text("""
            WITH query_embs AS (
                SELECT
                    (row_number() OVER ()) - 1 AS idx,
                    emb::vector AS emb
                FROM UNNEST(:emb_array::text[]) AS t(emb)
            )
            SELECT DISTINCT ON (q.idx)
                q.idx,
                c.meal_name,
                c.name_slug,
                c.image_url,
                c.thumbnail_url,
                c.source,
                c.confidence,
                c.text_embedding <=> q.emb AS distance
            FROM query_embs q
            CROSS JOIN LATERAL (
                SELECT * FROM meal_image_cache
                ORDER BY text_embedding <=> q.emb
                LIMIT 1
            ) c
            ORDER BY q.idx, distance
        """)

        rows = self._session.execute(stmt, {"emb_array": emb_strs}).fetchall()
        results: list[Optional[CachedImage]] = [None] * len(text_embeddings)

        for row in rows:
            idx = int(row[0])
            results[idx] = CachedImage(
                meal_name=row[1],
                name_slug=row[2],
                image_url=row[3],
                thumbnail_url=row[4],
                source=row[5],
                confidence=float(row[6]) if row[6] is not None else None,
                cosine=1.0 - float(row[7]),
            )

        return results

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
        self._session.execute(
            stmt,
            {
                "meal_name": record.meal_name,
                "name_slug": record.name_slug,
                "emb": emb_literal,
                "image_url": record.image_url,
                "thumbnail_url": record.thumbnail_url,
                "source": record.source,
                "confidence": record.confidence,
            },
        )
        self._session.commit()
