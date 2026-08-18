"""Async repository for durable meal recommendation candidate rows."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationAlreadyLoggedError,
    MealRecommendationIdempotencyConflictError,
    MealRecommendationInvalidAlternativeError,
    MealRecommendationNotFoundError,
    MealRecommendationNotLoggedError,
    MealRecommendationPersistenceConflictError,
    MealRecommendationTerminalStateError,
    MealRecommendationVersionConflictError,
)
from src.domain.model.meal_recommendation import (
    CatalogMeal,
    MealRecommendationAlternative,
    PersistedMealRecommendationCandidate,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
    PersistedMealRecommendationSlotMutationResult,
)
from src.domain.ports.meal_recommendation_plan_repository_port import (
    MealRecommendationPlanRepositoryPort,
)
from src.infra.database.models.food_reference_model import FoodReferenceModel
from src.infra.database.models.meal_recommendation import (
    MealCatalogIngredientORM,
    MealCatalogORM,
    MealRecommendationOperationORM,
    MealRecommendationORM,
)
from src.infra.repositories.catalog_recipe_repository_async import _meal_to_domain


class AsyncMealRecommendationPlanRepository(MealRecommendationPlanRepositoryPort):
    """Repository for owner-scoped durable recommendation batches."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> PersistedMealRecommendationPlan | None:
        rows = await self._load_batch(user_id=user_id, batch_id=plan_id)
        return _rows_to_plan(rows) if rows else None

    async def get_summary(
        self,
        *,
        user_id: str,
        plan_id: str,
    ) -> PersistedMealRecommendationPlan | None:
        rows = await self._load_selected_slots(user_id=user_id, batch_id=plan_id)
        return _rows_to_summary(rows) if rows else None

    async def get_slot_detail(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
    ) -> PersistedMealRecommendationSlot | None:
        anchor = await self._load_anchor(user_id=user_id, batch_id=plan_id)
        if anchor is None:
            return None
        rows = await self._load_slot(user_id=user_id, batch_id=plan_id, slot_id=slot_id)
        if not rows:
            return None
        return _rows_to_slot_detail(anchor, rows)

    async def get_by_idempotency_key(
        self,
        *,
        user_id: str,
        operation: str,
        idempotency_key: str,
    ) -> PersistedMealRecommendationPlan | None:
        result = await self._session.execute(
            select(MealRecommendationORM.id)
            .where(MealRecommendationORM.user_id == user_id)
            .where(MealRecommendationORM.operation == operation)
            .where(MealRecommendationORM.idempotency_key == idempotency_key)
            .where(MealRecommendationORM.id == MealRecommendationORM.batch_id)
        )
        batch_id = result.scalar_one_or_none()
        if batch_id is None:
            return None
        rows = await self._load_batch(user_id=user_id, batch_id=cast(str, batch_id))
        return _rows_to_plan(rows) if rows else None

    async def lock_generation_for_user(self, *, user_id: str) -> None:
        await self._session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtext(f"meal_recommendation_plan:{user_id}")
                )
            )
        )

    async def save_new_active_plan(
        self,
        plan: PersistedMealRecommendationPlan,
    ) -> PersistedMealRecommendationPlan:
        rows = _plan_to_rows(plan)
        try:
            async with self._session.begin_nested():
                await self._session.execute(
                    update(MealRecommendationORM)
                    .where(MealRecommendationORM.user_id == plan.user_id)
                    .where(MealRecommendationORM.status == "active")
                    .where(MealRecommendationORM.id == MealRecommendationORM.batch_id)
                    .values(status="superseded", superseded_at=datetime.now(UTC))
                )
                for row in rows:
                    self._session.add(row)
                await self._session.flush()
        except IntegrityError as exc:
            raise MealRecommendationPersistenceConflictError from exc
        return plan

    async def swap_slot(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
        expected_version: int,
        alternative_catalog_meal_id: str | None,
        reason: str,
        replenishment_alternatives: tuple[MealRecommendationAlternative, ...] = (),
    ) -> PersistedMealRecommendationSlotMutationResult:
        replay = await self._get_operation_replay(
            user_id=user_id, operation_type="swap", request_id=request_id
        )
        fingerprint = _operation_fingerprint(
            plan_id=plan_id,
            slot_id=slot_id,
            expected_version=expected_version,
            requested_catalog_meal_id=alternative_catalog_meal_id,
            reason=reason,
        )
        if replay is not None:
            if cast(str, replay.request_fingerprint) != fingerprint:
                raise MealRecommendationIdempotencyConflictError
            anchor = await self._load_anchor(user_id=user_id, batch_id=plan_id)
            if anchor is None:
                raise MealRecommendationNotFoundError
            slot = await self.get_slot_detail(
                user_id=user_id, plan_id=plan_id, slot_id=slot_id
            )
            if slot is None:
                raise MealRecommendationNotFoundError
            return PersistedMealRecommendationSlotMutationResult(
                plan_id=plan_id,
                user_id=user_id,
                slot=slot,
            )

        anchor, rows = await self._load_slot_for_update(
            user_id=user_id, batch_id=plan_id, slot_id=slot_id
        )
        if not rows:
            raise MealRecommendationNotFoundError
        replay = await self._get_operation_replay(
            user_id=user_id, operation_type="swap", request_id=request_id
        )
        if replay is not None:
            if cast(str, replay.request_fingerprint) != fingerprint:
                raise MealRecommendationIdempotencyConflictError
            return PersistedMealRecommendationSlotMutationResult(
                plan_id=plan_id,
                user_id=user_id,
                slot=_rows_to_slot_detail(anchor, rows),
            )
        selected = _selected_row(rows, slot_id)
        if int(cast(int, selected.selection_version)) != expected_version:
            raise MealRecommendationVersionConflictError
        if selected.logged_at or getattr(selected, "skipped_at", None):
            raise MealRecommendationTerminalStateError

        alternatives = sorted(
            (
                row
                for row in rows
                if cast(str, row.slot_id) == slot_id
                and not cast(bool, row.is_selected)
                and getattr(row, "retired_at", None) is None
                and getattr(row, "seen_at", None) is None
            ),
            key=lambda item: cast(int, item.candidate_rank),
        )
        if alternative_catalog_meal_id is None:
            target = alternatives[0] if alternatives else None
        else:
            target = next(
                (
                    row
                    for row in alternatives
                    if cast(str, row.catalog_meal_id) == alternative_catalog_meal_id
                ),
                None,
            )
        outcome = "stored_candidate"
        if (
            target is None
            and alternative_catalog_meal_id is None
            and replenishment_alternatives
        ):
            now = datetime.now(UTC)
            active_rows = [
                row
                for row in rows
                if getattr(row, "retired_at", None) is None
                and not cast(bool, row.is_selected)
            ]
            for row in active_rows:
                row.retired_at = now  # type: ignore[assignment]
            next_rank = (
                max((cast(int, row.candidate_rank) for row in rows), default=0) + 1
            )
            new_rows = []
            for position, alternative in enumerate(replenishment_alternatives):
                row = MealRecommendationORM(
                    id=str(uuid.uuid4()),
                    batch_id=plan_id,
                    slot_id=slot_id,
                    recommendation_date=selected.recommendation_date,
                    meal_type=selected.meal_type,
                    catalog_meal_id=alternative.catalog_meal.id,
                    candidate_rank=next_rank + position,
                    is_selected=position == 0,
                    score=Decimal(str(alternative.score)),
                    selection_version=expected_version + 1,
                    seen_at=now if position == 0 else None,
                )
                row._domain_catalog_meal = alternative.catalog_meal
                self._session.add(row)
                new_rows.append(row)
            target = new_rows[0]
            rows.extend(new_rows)
            outcome = "replenished_candidate"
        if target is None:
            raise MealRecommendationInvalidAlternativeError

        new_version = expected_version + 1
        selected.is_selected = False  # type: ignore[assignment]
        selected.selection_version = new_version  # type: ignore[assignment]
        selected_seen_at = getattr(selected, "seen_at", None) or datetime.now(UTC)
        selected.seen_at = selected_seen_at  # type: ignore[assignment]
        selected.retired_at = selected_seen_at  # type: ignore[assignment]
        await self._flush_operations()

        if outcome == "replenished_candidate":
            target_id = cast(str, target.id)
            batch_rows = await self._load_batch(user_id=user_id, batch_id=plan_id)
            anchor = _anchor_row(batch_rows)
            rows = [row for row in batch_rows if cast(str, row.slot_id) == slot_id]
            target = next(
                (row for row in rows if cast(str, row.id) == target_id),
                None,
            )
            if anchor is None or target is None:
                raise MealRecommendationNotFoundError

        for row in rows:
            if cast(str, row.slot_id) != slot_id:
                continue
            row.selection_version = new_version  # type: ignore[assignment]
        target.is_selected = True  # type: ignore[assignment]
        target.logged_at = None  # type: ignore[assignment]
        target.seen_at = getattr(target, "seen_at", None) or datetime.now(UTC)  # type: ignore[assignment]
        self._session.add(
            MealRecommendationOperationORM(
                user_id=user_id,
                batch_id=plan_id,
                slot_id=slot_id,
                operation_type="swap",
                request_id=request_id,
                request_fingerprint=fingerprint,
                result_selection_version=new_version,
                result_catalog_meal_id=cast(str, target.catalog_meal_id),
            )
        )
        await self._flush_operations()
        return PersistedMealRecommendationSlotMutationResult(
            plan_id=plan_id,
            user_id=user_id,
            slot=_rows_to_slot_detail(anchor, rows),
            outcome=outcome,
        )

    async def get_slot_replenishment_context(
        self, *, user_id: str, plan_id: str, slot_id: str
    ) -> (
        tuple[
            PersistedMealRecommendationSlot,
            frozenset[str],
            frozenset[str],
            str,
        ]
        | None
    ):
        rows = await self._load_batch(user_id=user_id, batch_id=plan_id)
        target_rows = [row for row in rows if cast(str, row.slot_id) == slot_id]
        if not target_rows:
            return None
        anchor = _anchor_row(rows)
        if anchor is None:
            return None
        target = _rows_to_slot_detail(anchor, target_rows)
        seen_ids = frozenset(
            cast(str, row.catalog_meal_id)
            for row in target_rows
            if getattr(row, "seen_at", None) is not None
        )
        other_selected_ids = frozenset(
            cast(str, row.catalog_meal_id)
            for row in rows
            if cast(str, row.slot_id) != slot_id and cast(bool, row.is_selected)
        )
        return target, seen_ids, other_selected_ids, cast(str, anchor.timezone)

    async def mark_shown(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_ids: tuple[str, ...],
    ) -> None:
        if not slot_ids:
            return
        if await self._load_anchor(user_id=user_id, batch_id=plan_id) is None:
            return
        await self._session.execute(
            update(MealRecommendationORM)
            .where(MealRecommendationORM.batch_id == plan_id)
            .where(MealRecommendationORM.slot_id.in_(slot_ids))
            .where(MealRecommendationORM.is_selected.is_(True))
            .where(MealRecommendationORM.shown_at.is_(None))
            .values(shown_at=datetime.now(UTC))
        )

    async def skip_slot(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
    ) -> PersistedMealRecommendationSlotMutationResult:
        fingerprint = _operation_fingerprint(plan_id=plan_id, slot_id=slot_id)
        replay = await self._get_operation_replay(
            user_id=user_id, operation_type="skip", request_id=request_id
        )
        if replay is not None:
            if cast(str, replay.request_fingerprint) != fingerprint:
                raise MealRecommendationIdempotencyConflictError
            slot = await self.get_slot_detail(
                user_id=user_id,
                plan_id=plan_id,
                slot_id=slot_id,
            )
            if slot is None:
                raise MealRecommendationNotFoundError
            return PersistedMealRecommendationSlotMutationResult(
                plan_id=plan_id,
                user_id=user_id,
                slot=slot,
            )

        anchor, rows = await self._load_slot_for_update(
            user_id=user_id, batch_id=plan_id, slot_id=slot_id
        )
        if not rows:
            raise MealRecommendationNotFoundError
        replay = await self._get_operation_replay(
            user_id=user_id, operation_type="skip", request_id=request_id
        )
        if replay is not None:
            if cast(str, replay.request_fingerprint) != fingerprint:
                raise MealRecommendationIdempotencyConflictError
            return PersistedMealRecommendationSlotMutationResult(
                plan_id=plan_id,
                user_id=user_id,
                slot=_rows_to_slot_detail(anchor, rows),
            )
        selected = _selected_row(rows, slot_id)
        if (
            selected.logged_meal_id
            or selected.logged_at
            or getattr(selected, "skipped_at", None)
        ):
            raise MealRecommendationTerminalStateError
        selected.skipped_at = datetime.now(UTC)  # type: ignore[assignment]
        self._session.add(
            MealRecommendationOperationORM(
                user_id=user_id,
                batch_id=plan_id,
                slot_id=slot_id,
                operation_type="skip",
                request_id=request_id,
                request_fingerprint=fingerprint,
            )
        )
        await self._flush_operations()
        return PersistedMealRecommendationSlotMutationResult(
            plan_id=plan_id,
            user_id=user_id,
            slot=_rows_to_slot_detail(anchor, rows),
        )

    async def claim_slot_log(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
    ) -> tuple[PersistedMealRecommendationPlan, PersistedMealRecommendationSlot, bool]:
        replay = await self._get_operation_replay(
            user_id=user_id, operation_type="log", request_id=request_id
        )
        anchor, rows = await self._load_slot_for_update(
            user_id=user_id, batch_id=plan_id, slot_id=slot_id
        )
        if not rows:
            raise MealRecommendationNotFoundError
        slot = _rows_to_slot_detail(anchor, rows)
        plan = _plan_from_anchor_and_slot(anchor, slot)
        if replay is not None:
            if (
                cast(str, replay.batch_id) != plan_id
                or cast(str, replay.slot_id) != slot_id
            ):
                raise MealRecommendationIdempotencyConflictError
            logged_meal_id = cast(
                str | None, getattr(replay, "result_logged_meal_id", None)
            )
            if not logged_meal_id:
                raise MealRecommendationIdempotencyConflictError
            if cast(
                str | None, getattr(replay, "request_fingerprint", None)
            ) != _operation_fingerprint(
                plan_id=plan_id,
                slot_id=slot_id,
                meal_id=logged_meal_id,
            ):
                raise MealRecommendationIdempotencyConflictError
            if slot.logged_meal_id != logged_meal_id:
                slot = replace(slot, logged_meal_id=logged_meal_id)
                plan = _plan_from_anchor_and_slot(anchor, slot)
            return plan, slot, True
        selected = _selected_row(rows, slot_id)
        if selected.logged_meal_id:
            raise MealRecommendationAlreadyLoggedError
        if getattr(selected, "skipped_at", None):
            raise MealRecommendationTerminalStateError
        return plan, slot, False

    async def finalize_slot_logged(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
        meal_id: str,
    ) -> PersistedMealRecommendationSlotMutationResult:
        anchor, rows = await self._load_slot_for_update(
            user_id=user_id, batch_id=plan_id, slot_id=slot_id
        )
        if not rows:
            raise MealRecommendationNotFoundError
        selected = _selected_row(rows, slot_id)
        if selected.logged_meal_id:
            if cast(str | None, selected.logged_meal_id) == meal_id:
                return PersistedMealRecommendationSlotMutationResult(
                    plan_id=plan_id,
                    user_id=user_id,
                    slot=_rows_to_slot_detail(anchor, rows),
                )
            raise MealRecommendationAlreadyLoggedError
        if getattr(selected, "skipped_at", None):
            raise MealRecommendationTerminalStateError
        now = datetime.now(UTC)
        selected.logged_meal_id = meal_id  # type: ignore[assignment]
        selected.logged_at = now  # type: ignore[assignment]
        self._session.add(
            MealRecommendationOperationORM(
                user_id=user_id,
                batch_id=plan_id,
                slot_id=slot_id,
                operation_type="log",
                request_id=request_id,
                request_fingerprint=_operation_fingerprint(
                    plan_id=plan_id,
                    slot_id=slot_id,
                    meal_id=meal_id,
                ),
                result_logged_meal_id=meal_id,
            )
        )
        await self._flush_operations()
        return PersistedMealRecommendationSlotMutationResult(
            plan_id=plan_id,
            user_id=user_id,
            slot=_rows_to_slot_detail(anchor, rows),
        )

    async def claim_slot_relog(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
    ) -> tuple[
        PersistedMealRecommendationPlan,
        PersistedMealRecommendationSlot,
        bool,
        str | None,
    ]:
        replay = await self._get_operation_replay(
            user_id=user_id, operation_type="relog", request_id=request_id
        )
        anchor, rows = await self._load_slot_for_update(
            user_id=user_id, batch_id=plan_id, slot_id=slot_id
        )
        if not rows:
            raise MealRecommendationNotFoundError
        slot = _rows_to_slot_detail(anchor, rows)
        plan = _plan_from_anchor_and_slot(anchor, slot)
        if replay is not None:
            if (
                cast(str, replay.batch_id) != plan_id
                or cast(str, replay.slot_id) != slot_id
            ):
                raise MealRecommendationIdempotencyConflictError
            logged_meal_id = cast(
                str | None, getattr(replay, "result_logged_meal_id", None)
            )
            if not logged_meal_id:
                raise MealRecommendationIdempotencyConflictError
            if cast(
                str | None, getattr(replay, "request_fingerprint", None)
            ) != _operation_fingerprint(
                plan_id=plan_id,
                slot_id=slot_id,
                meal_id=logged_meal_id,
            ):
                raise MealRecommendationIdempotencyConflictError
            return plan, slot, True, logged_meal_id
        selected = _selected_row(rows, slot_id)
        if getattr(selected, "skipped_at", None):
            raise MealRecommendationTerminalStateError
        if not selected.logged_meal_id:
            raise MealRecommendationNotLoggedError
        return plan, slot, False, None

    async def finalize_slot_relogged(
        self,
        *,
        user_id: str,
        plan_id: str,
        slot_id: str,
        request_id: str,
        meal_id: str,
    ) -> PersistedMealRecommendationSlotMutationResult:
        anchor, rows = await self._load_slot_for_update(
            user_id=user_id, batch_id=plan_id, slot_id=slot_id
        )
        if not rows:
            raise MealRecommendationNotFoundError
        selected = _selected_row(rows, slot_id)
        if getattr(selected, "skipped_at", None):
            raise MealRecommendationTerminalStateError
        if not selected.logged_meal_id:
            raise MealRecommendationNotLoggedError
        self._session.add(
            MealRecommendationOperationORM(
                user_id=user_id,
                batch_id=plan_id,
                slot_id=slot_id,
                operation_type="relog",
                request_id=request_id,
                request_fingerprint=_operation_fingerprint(
                    plan_id=plan_id,
                    slot_id=slot_id,
                    meal_id=meal_id,
                ),
                result_logged_meal_id=meal_id,
            )
        )
        await self._flush_operations()
        return PersistedMealRecommendationSlotMutationResult(
            plan_id=plan_id,
            user_id=user_id,
            slot=_rows_to_slot_detail(anchor, rows),
            meal_id=meal_id,
        )

    async def clear_links_for_deleted_meal(self, *, meal_id: str) -> None:
        """Detach recommendation state from a meal about to be hard-deleted.

        ``logged_meal_id`` FKs use ON DELETE SET NULL. That leaves ``logged_at``
        set and breaks ``ck_meal_recommendations_logged_coherent``. Log operation
        rows also require ``result_logged_meal_id`` non-null, so SET NULL there
        violates ``ck_meal_recommendation_operations_payload``. Clear both sides
        before the meal row is removed.
        """
        await self._session.execute(
            update(MealRecommendationORM)
            .where(MealRecommendationORM.logged_meal_id == meal_id)
            .values(logged_meal_id=None, logged_at=None)
        )
        await self._session.execute(
            delete(MealRecommendationOperationORM).where(
                MealRecommendationOperationORM.result_logged_meal_id == meal_id
            )
        )
        # Plain flush — do not use _flush_operations(), which remaps IntegrityError
        # into meal-recommendation swap/idempotency domain errors (wrong for delete).
        await self._session.flush()

    async def _load_batch(
        self, *, user_id: str, batch_id: str
    ) -> list[MealRecommendationORM]:
        stmt = (
            select(MealRecommendationORM)
            .where(MealRecommendationORM.batch_id == batch_id)
            .options(_recommendation_catalog_meal_load_options())
            .order_by(
                MealRecommendationORM.recommendation_date,
                MealRecommendationORM.meal_type,
                MealRecommendationORM.candidate_rank,
            )
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().unique().all())
        anchor = _anchor_row(rows)
        if anchor is None or cast(str | None, anchor.user_id) != user_id:
            return []
        return rows

    async def _load_selected_slots(
        self, *, user_id: str, batch_id: str
    ) -> list[MealRecommendationORM]:
        stmt = (
            select(MealRecommendationORM)
            .where(MealRecommendationORM.batch_id == batch_id)
            .where(MealRecommendationORM.is_selected.is_(True))
            .options(_recommendation_catalog_meal_load_options())
            .order_by(
                MealRecommendationORM.recommendation_date,
                MealRecommendationORM.meal_type,
                MealRecommendationORM.candidate_rank,
            )
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().unique().all())
        anchor = _anchor_row(rows)
        if anchor is None or cast(str | None, anchor.user_id) != user_id:
            return []
        return rows

    async def _load_anchor(
        self, *, user_id: str, batch_id: str
    ) -> MealRecommendationORM | None:
        result = await self._session.execute(
            select(MealRecommendationORM)
            .where(MealRecommendationORM.id == batch_id)
            .where(MealRecommendationORM.batch_id == batch_id)
            .where(MealRecommendationORM.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _load_slot(
        self, *, user_id: str, batch_id: str, slot_id: str
    ) -> list[MealRecommendationORM]:
        if await self._load_anchor(user_id=user_id, batch_id=batch_id) is None:
            return []
        stmt = (
            select(MealRecommendationORM)
            .where(MealRecommendationORM.batch_id == batch_id)
            .where(MealRecommendationORM.slot_id == slot_id)
            .where(MealRecommendationORM.retired_at.is_(None))
            .options(_recommendation_catalog_meal_load_options())
            .order_by(MealRecommendationORM.candidate_rank)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def _load_batch_for_update(
        self, *, user_id: str, batch_id: str
    ) -> list[MealRecommendationORM]:
        stmt = (
            select(MealRecommendationORM)
            .where(MealRecommendationORM.batch_id == batch_id)
            .options(_recommendation_catalog_meal_load_options())
            .order_by(
                MealRecommendationORM.recommendation_date,
                MealRecommendationORM.meal_type,
                MealRecommendationORM.candidate_rank,
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().unique().all())
        anchor = _anchor_row(rows)
        if anchor is None or cast(str | None, anchor.user_id) != user_id:
            return []
        return rows

    async def _load_slot_for_update(
        self, *, user_id: str, batch_id: str, slot_id: str
    ) -> tuple[MealRecommendationORM, list[MealRecommendationORM]]:
        anchor = await self._load_anchor(user_id=user_id, batch_id=batch_id)
        if anchor is None:
            raise MealRecommendationNotFoundError
        stmt = (
            select(MealRecommendationORM)
            .where(MealRecommendationORM.batch_id == batch_id)
            .where(MealRecommendationORM.slot_id == slot_id)
            .options(_recommendation_catalog_meal_load_options())
            .order_by(MealRecommendationORM.candidate_rank)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return anchor, list(result.scalars().unique().all())

    async def _get_operation_replay(
        self, *, user_id: str, operation_type: str, request_id: str
    ) -> MealRecommendationOperationORM | None:
        result = await self._session.execute(
            select(MealRecommendationOperationORM)
            .where(MealRecommendationOperationORM.user_id == user_id)
            .where(MealRecommendationOperationORM.operation_type == operation_type)
            .where(MealRecommendationOperationORM.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def _flush_operations(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:
            detail = f"{exc.orig!s} {exc!s}"
            if "uq_meal_recommendation_operations_user_type_request" in detail:
                raise MealRecommendationIdempotencyConflictError from exc
            raise MealRecommendationInvalidAlternativeError from exc


def _plan_to_rows(plan: PersistedMealRecommendationPlan) -> list[MealRecommendationORM]:
    rows: list[MealRecommendationORM] = []
    for slot in plan.slots:
        candidates = _slot_candidates(slot)
        for candidate in candidates:
            rows.append(
                MealRecommendationORM(
                    id=candidate.id,
                    batch_id=plan.id,
                    slot_id=slot.id,
                    recommendation_date=slot.slot_date,
                    meal_type=slot.meal_type,
                    catalog_meal_id=candidate.catalog_meal_id,
                    candidate_rank=candidate.candidate_rank,
                    is_selected=candidate.is_selected,
                    score=candidate.score,
                    selection_version=candidate.selection_version,
                    seen_at=candidate.seen_at,
                    retired_at=candidate.retired_at,
                    logged_at=candidate.logged_at,
                    logged_meal_id=candidate.logged_meal_id,
                    shown_at=candidate.shown_at,
                    skipped_at=candidate.skipped_at,
                    user_id=plan.user_id if candidate.id == plan.id else None,
                    status=plan.status if candidate.id == plan.id else None,
                    timezone=plan.timezone if candidate.id == plan.id else None,
                    start_date=plan.start_date if candidate.id == plan.id else None,
                    target_calories=plan.daily_calories
                    if candidate.id == plan.id
                    else None,
                    operation=plan.operation if candidate.id == plan.id else None,
                    idempotency_key=plan.idempotency_key
                    if candidate.id == plan.id
                    else None,
                    request_fingerprint=plan.request_fingerprint
                    if candidate.id == plan.id
                    else None,
                )
            )
    return rows


def _slot_candidates(
    slot: PersistedMealRecommendationSlot,
) -> tuple[PersistedMealRecommendationCandidate, ...]:
    if slot.selected is not None:
        return (slot.selected, *slot.alternatives)
    return (
        PersistedMealRecommendationCandidate(
            id=slot.id,
            slot_id=slot.id,
            recommendation_date=slot.slot_date,
            meal_type=slot.meal_type,
            catalog_meal_id=slot.catalog_meal_id,
            candidate_rank=0,
            is_selected=True,
            score=Decimal(str(slot.score)),
            selection_version=slot.selection_version,
            logged_meal_id=slot.logged_meal_id,
            shown_at=slot.shown_at,
            skipped_at=slot.skipped_at,
        ),
        *slot.alternatives,
    )


def _rows_to_plan(rows: list[MealRecommendationORM]) -> PersistedMealRecommendationPlan:
    anchor = _anchor_row(rows)
    if anchor is None:
        raise MealRecommendationNotFoundError
    slots: list[PersistedMealRecommendationSlot] = []
    grouped: dict[str, list[MealRecommendationORM]] = {}
    for row in rows:
        if getattr(row, "retired_at", None) is None:
            grouped.setdefault(cast(str, row.slot_id), []).append(row)

    for position, slot_rows in enumerate(grouped.values()):
        ordered = sorted(slot_rows, key=lambda item: cast(int, item.candidate_rank))
        selected = next(row for row in ordered if cast(bool, row.is_selected))
        selected_candidate = _candidate_to_domain(selected)
        alternatives = tuple(
            _candidate_to_domain(row)
            for row in ordered
            if cast(str, row.id) != selected_candidate.id
        )
        slots.append(
            PersistedMealRecommendationSlot(
                id=cast(str, selected.slot_id),
                slot_date=cast(date, selected.recommendation_date),
                day_index=(
                    cast(date, selected.recommendation_date)
                    - cast(date, anchor.start_date)
                ).days,
                meal_type=cast(str, selected.meal_type),
                catalog_meal_id=cast(str, selected.catalog_meal_id),
                target_calories=cast(int, anchor.target_calories),
                score=float(selected.score),
                position=position,
                selection_version=cast(int, selected.selection_version),
                logged_meal_id=cast(str | None, selected.logged_meal_id),
                shown_at=cast(datetime | None, getattr(selected, "shown_at", None)),
                skipped_at=cast(datetime | None, getattr(selected, "skipped_at", None)),
                selected=selected_candidate,
                alternatives=alternatives,
            )
        )

    return PersistedMealRecommendationPlan(
        id=cast(str, anchor.id),
        user_id=cast(str, anchor.user_id),
        status=cast(str, anchor.status),
        timezone=cast(str, anchor.timezone),
        start_date=cast(date, anchor.start_date),
        daily_calories=cast(int, anchor.target_calories),
        operation=cast(str, anchor.operation),
        idempotency_key=cast(str, anchor.idempotency_key),
        request_fingerprint=cast(str, anchor.request_fingerprint),
        created_at=cast(datetime | None, anchor.created_at),
        slots=tuple(slots),
    )


def _rows_to_summary(
    rows: list[MealRecommendationORM],
) -> PersistedMealRecommendationPlan:
    anchor = _anchor_row(rows)
    if anchor is None:
        raise MealRecommendationNotFoundError
    selected_rows = sorted(
        (row for row in rows if cast(bool, row.is_selected)),
        key=lambda item: (
            cast(date, item.recommendation_date),
            cast(str, item.meal_type),
            cast(int, item.candidate_rank),
        ),
    )
    slots = []
    for position, row in enumerate(selected_rows):
        selected_candidate = _candidate_to_domain(row)
        slots.append(
            PersistedMealRecommendationSlot(
                id=cast(str, row.slot_id),
                slot_date=cast(date, row.recommendation_date),
                day_index=(
                    cast(date, row.recommendation_date) - cast(date, anchor.start_date)
                ).days,
                meal_type=cast(str, row.meal_type),
                catalog_meal_id=cast(str, row.catalog_meal_id),
                target_calories=cast(int, anchor.target_calories),
                score=float(row.score),
                position=position,
                selection_version=cast(int, row.selection_version),
                logged_meal_id=cast(str | None, row.logged_meal_id),
                shown_at=cast(datetime | None, getattr(row, "shown_at", None)),
                skipped_at=cast(datetime | None, getattr(row, "skipped_at", None)),
                selected=selected_candidate,
                alternatives=(),
            )
        )
    return PersistedMealRecommendationPlan(
        id=cast(str, anchor.id),
        user_id=cast(str, anchor.user_id),
        status=cast(str, anchor.status),
        timezone=cast(str, anchor.timezone),
        start_date=cast(date, anchor.start_date),
        daily_calories=cast(int, anchor.target_calories),
        operation=cast(str, anchor.operation),
        idempotency_key=cast(str, anchor.idempotency_key),
        request_fingerprint=cast(str, anchor.request_fingerprint),
        created_at=cast(datetime | None, anchor.created_at),
        slots=tuple(slots),
    )


def _rows_to_slot_detail(
    anchor: MealRecommendationORM,
    rows: list[MealRecommendationORM],
) -> PersistedMealRecommendationSlot:
    ordered = sorted(
        (row for row in rows if getattr(row, "retired_at", None) is None),
        key=lambda item: cast(int, item.candidate_rank),
    )
    selected = next((row for row in ordered if cast(bool, row.is_selected)), None)
    if selected is None:
        raise MealRecommendationNotFoundError
    selected_candidate = _candidate_to_domain(selected)
    alternatives = tuple(
        _candidate_to_domain(row)
        for row in ordered
        if cast(str, row.id) != selected_candidate.id
    )
    return PersistedMealRecommendationSlot(
        id=cast(str, selected.slot_id),
        slot_date=cast(date, selected.recommendation_date),
        day_index=(
            cast(date, selected.recommendation_date) - cast(date, anchor.start_date)
        ).days,
        meal_type=cast(str, selected.meal_type),
        catalog_meal_id=cast(str, selected.catalog_meal_id),
        target_calories=cast(int, anchor.target_calories),
        score=float(selected.score),
        position=0,
        selection_version=cast(int, selected.selection_version),
        logged_meal_id=cast(str | None, selected.logged_meal_id),
        shown_at=cast(datetime | None, getattr(selected, "shown_at", None)),
        skipped_at=cast(datetime | None, getattr(selected, "skipped_at", None)),
        selected=selected_candidate,
        alternatives=alternatives,
    )


def _plan_from_anchor_and_slot(
    anchor: MealRecommendationORM,
    slot: PersistedMealRecommendationSlot,
) -> PersistedMealRecommendationPlan:
    return PersistedMealRecommendationPlan(
        id=cast(str, anchor.id),
        user_id=cast(str, anchor.user_id),
        status=cast(str, anchor.status),
        timezone=cast(str, anchor.timezone),
        start_date=cast(date, anchor.start_date),
        daily_calories=cast(int, anchor.target_calories),
        operation=cast(str, anchor.operation),
        idempotency_key=cast(str, anchor.idempotency_key),
        request_fingerprint=cast(str, anchor.request_fingerprint),
        created_at=cast(datetime | None, anchor.created_at),
        slots=(slot,),
    )


def _candidate_to_domain(
    row: MealRecommendationORM,
) -> PersistedMealRecommendationCandidate:
    return PersistedMealRecommendationCandidate(
        id=cast(str, row.id),
        slot_id=cast(str, row.slot_id),
        recommendation_date=cast(date, row.recommendation_date),
        meal_type=cast(str, row.meal_type),
        catalog_meal_id=cast(str, row.catalog_meal_id),
        candidate_rank=cast(int, row.candidate_rank),
        is_selected=cast(bool, row.is_selected),
        score=cast(Decimal, row.score),
        selection_version=cast(int, row.selection_version),
        catalog_meal=_candidate_catalog_meal(row),
        seen_at=cast(datetime | None, getattr(row, "seen_at", None)),
        retired_at=cast(datetime | None, getattr(row, "retired_at", None)),
        logged_at=cast(datetime | None, row.logged_at),
        logged_meal_id=cast(str | None, row.logged_meal_id),
        shown_at=cast(datetime | None, getattr(row, "shown_at", None)),
        skipped_at=cast(datetime | None, getattr(row, "skipped_at", None)),
    )


def _candidate_catalog_meal(row: MealRecommendationORM) -> CatalogMeal | None:
    domain_catalog_meal = getattr(row, "_domain_catalog_meal", None)
    if domain_catalog_meal is not None:
        return domain_catalog_meal
    catalog_meal = row.catalog_meal
    if catalog_meal is None:
        return None
    if isinstance(catalog_meal, CatalogMeal):
        return catalog_meal
    return _meal_to_domain(catalog_meal)


def _anchor_row(rows: list[MealRecommendationORM]) -> MealRecommendationORM | None:
    return next(
        (row for row in rows if cast(str, row.id) == cast(str, row.batch_id)), None
    )


def _selected_row(
    rows: list[MealRecommendationORM], slot_id: str
) -> MealRecommendationORM:
    for row in rows:
        if cast(str, row.slot_id) == slot_id and cast(bool, row.is_selected):
            return row
    raise MealRecommendationNotFoundError


def _operation_fingerprint(**payload) -> str:
    import hashlib
    import json

    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _recommendation_catalog_meal_load_options():
    return (
        selectinload(MealRecommendationORM.catalog_meal)
        .selectinload(MealCatalogORM.ingredients)
        .selectinload(MealCatalogIngredientORM.food_reference)
        .selectinload(FoodReferenceModel.serving_size_rows)
    )
