"""Handler for durable three-day meal recommendation creation."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta

from src.app.commands.meal_recommendation import (
    CreateThreeDayMealRecommendationCommand,
)
from src.app.events.base import EventHandler, handles
from src.app.services.meal_recommendation_history_projector import (
    MealRecommendationHistoryProjector,
)
from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationCatalogUnavailableError,
    MealRecommendationIdempotencyConflictError,
    MealRecommendationInsufficientCatalogError,
    MealRecommendationPersistenceConflictError,
)
from src.domain.model.meal_recommendation import (
    MealRecommendationInsufficiency,
    PersistedMealRecommendationAlternative,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.domain.services.meal_recommendation.three_day_plan_optimizer import (
    ThreeDayPlanOptimizer,
)


@handles(CreateThreeDayMealRecommendationCommand)
class CreateThreeDayMealRecommendationCommandHandler(
    EventHandler[
        CreateThreeDayMealRecommendationCommand,
        PersistedMealRecommendationPlan,
    ]
):
    """Create an active durable plan from the active catalog release."""

    def __init__(
        self,
        uow,
        optimizer: ThreeDayPlanOptimizer | None = None,
        history_projector: MealRecommendationHistoryProjector | None = None,
    ):
        self.uow = uow
        self.optimizer = optimizer or ThreeDayPlanOptimizer()
        self.history_projector = history_projector or MealRecommendationHistoryProjector()

    async def handle(
        self,
        command: CreateThreeDayMealRecommendationCommand,
    ) -> PersistedMealRecommendationPlan:
        fingerprint = _request_fingerprint(command)
        async with self.uow as uow:
            await uow.meal_recommendation_plans.lock_generation_for_user(
                user_id=command.user_id
            )
            existing = await uow.meal_recommendation_plans.get_by_idempotency_key(
                user_id=command.user_id,
                operation=command.operation,
                idempotency_key=command.idempotency_key,
            )
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise MealRecommendationIdempotencyConflictError
                return existing

            release = await uow.catalog_recipes.get_active_release()
            if release is None:
                raise MealRecommendationCatalogUnavailableError

            recipes = await uow.catalog_recipes.list_active_versions()
            affinity = await self.history_projector.build_affinity(
                uow,
                user_id=command.user_id,
                start_date=command.start_date,
                timezone=command.timezone,
            )
            result = self.optimizer.build_plan(
                recipes,
                daily_calories=command.daily_calories,
                affinity=affinity,
            )
            if isinstance(result, MealRecommendationInsufficiency):
                raise MealRecommendationInsufficientCatalogError(result.message)

            plan = _to_persisted_plan(command, fingerprint, release.id, result)
            try:
                return await uow.meal_recommendation_plans.save_new_active_plan(plan)
            except MealRecommendationPersistenceConflictError:
                replay = await uow.meal_recommendation_plans.get_by_idempotency_key(
                    user_id=command.user_id,
                    operation=command.operation,
                    idempotency_key=command.idempotency_key,
                )
                if replay is None:
                    raise
                if replay.request_fingerprint != fingerprint:
                    raise MealRecommendationIdempotencyConflictError from None
                return replay


def _to_persisted_plan(
    command: CreateThreeDayMealRecommendationCommand,
    fingerprint: str,
    catalog_release_id: str,
    plan,
) -> PersistedMealRecommendationPlan:
    slots: list[PersistedMealRecommendationSlot] = []
    for position, slot in enumerate(plan.slots):
        alternatives = tuple(
            PersistedMealRecommendationAlternative(
                id=str(uuid.uuid4()),
                recipe_version_id=alternative.recipe.id,
                target_calories=alternative.target_calories,
                score=alternative.score,
                position=alternative_position,
            )
            for alternative_position, alternative in enumerate(
                plan.alternatives[(slot.day_index, slot.meal_type)]
            )
        )
        slots.append(
            PersistedMealRecommendationSlot(
                id=str(uuid.uuid4()),
                slot_date=command.start_date + timedelta(days=slot.day_index),
                day_index=slot.day_index,
                meal_type=slot.meal_type,
                recipe_version_id=slot.recipe.id,
                target_calories=slot.target_calories,
                score=slot.score,
                position=position,
                alternatives=alternatives,
            )
        )
    return PersistedMealRecommendationPlan(
        id=str(uuid.uuid4()),
        user_id=command.user_id,
        status="active",
        timezone=command.timezone,
        start_date=command.start_date,
        daily_calories=command.daily_calories,
        algorithm_version=plan.algorithm_version,
        catalog_release_id=catalog_release_id,
        allergy_evaluated=False,
        operation=command.operation,
        idempotency_key=command.idempotency_key,
        request_fingerprint=fingerprint,
        slots=tuple(slots),
    )


def _request_fingerprint(command: CreateThreeDayMealRecommendationCommand) -> str:
    payload = {
        "daily_calories": command.daily_calories,
        "operation": command.operation,
        "start_date": command.start_date.isoformat(),
        "timezone": command.timezone,
        "user_id": command.user_id,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
