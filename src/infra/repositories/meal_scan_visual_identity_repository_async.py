"""Async repository for meal scan visual identities."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.meal_scan_visual_identity import MealScanVisualIdentity
from src.infra.database.models.meal_scan_visual_identity import (
    MealScanVisualIdentityORM,
)


def _to_domain(row: MealScanVisualIdentityORM) -> MealScanVisualIdentity:
    ingredients = row.ingredients or []
    if not isinstance(ingredients, list):
        ingredients = []
    signature = row.scene_signature or []
    return MealScanVisualIdentity(
        id=row.id,
        user_id=row.user_id,
        meal_id=row.meal_id,
        source=row.source,
        dish_slug=row.dish_slug,
        ingredients=tuple(str(item) for item in ingredients),
        container=row.container,
        background=row.background,
        identity_key=row.identity_key,
        scene_signature=tuple(float(v) for v in signature),
        created_at=row.created_at,
    )


class AsyncMealScanVisualIdentityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, identity: MealScanVisualIdentity) -> MealScanVisualIdentity:
        row = MealScanVisualIdentityORM(
            id=identity.id,
            user_id=identity.user_id,
            meal_id=identity.meal_id,
            source=identity.source,
            dish_slug=identity.dish_slug,
            ingredients=list(identity.ingredients),
            container=identity.container,
            background=identity.background,
            identity_key=identity.identity_key,
            scene_signature=list(identity.scene_signature),
            created_at=identity.created_at,
        )
        self.session.add(row)
        await self.session.flush()
        return _to_domain(row)

    async def list_by_user_source_dish(
        self,
        *,
        user_id: str,
        source: str,
        dish_slug: str,
        limit: int = 20,
    ) -> list[MealScanVisualIdentity]:
        result = await self.session.execute(
            select(MealScanVisualIdentityORM)
            .where(
                MealScanVisualIdentityORM.user_id == user_id,
                MealScanVisualIdentityORM.source == source,
                MealScanVisualIdentityORM.dish_slug == dish_slug,
            )
            .order_by(MealScanVisualIdentityORM.created_at.desc())
            .limit(limit)
        )
        return [_to_domain(row) for row in result.scalars().all()]

    async def find_by_identity_key(
        self,
        *,
        user_id: str,
        identity_key: str,
        source: str,
        limit: int = 5,
    ) -> list[MealScanVisualIdentity]:
        result = await self.session.execute(
            select(MealScanVisualIdentityORM)
            .where(
                MealScanVisualIdentityORM.user_id == user_id,
                MealScanVisualIdentityORM.source == source,
                MealScanVisualIdentityORM.identity_key == identity_key,
            )
            .order_by(MealScanVisualIdentityORM.created_at.desc())
            .limit(limit)
        )
        return [_to_domain(row) for row in result.scalars().all()]

    async def delete_by_meal_id(self, meal_id: str) -> None:
        await self.session.execute(
            delete(MealScanVisualIdentityORM).where(
                MealScanVisualIdentityORM.meal_id == meal_id
            )
        )

    async def count_for_user_source(self, *, user_id: str, source: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(MealScanVisualIdentityORM)
            .where(
                MealScanVisualIdentityORM.user_id == user_id,
                MealScanVisualIdentityORM.source == source,
            )
        )
        return int(result.scalar_one())
