"""Handler for logging recommended meals through normal meal persistence."""

import logging

from src.app.commands.meal_recommendation import LogRecommendedMealCommand
from src.app.events.base import EventHandler, handles
from src.app.services.recommended_meal_materialization_service import (
    RecommendedMealMaterializationService,
)
from src.domain.model.meal_recommendation import (
    PersistedMealRecommendationSlotMutationResult,
)

logger = logging.getLogger(__name__)


@handles(LogRecommendedMealCommand)
class LogRecommendedMealCommandHandler(
    EventHandler[
        LogRecommendedMealCommand,
        PersistedMealRecommendationSlotMutationResult,
    ]
):
    def __init__(
        self,
        uow,
        materializer: RecommendedMealMaterializationService | None = None,
    ):
        self.uow = uow
        self.materializer = materializer or RecommendedMealMaterializationService()

    async def handle(
        self, command: LogRecommendedMealCommand
    ) -> PersistedMealRecommendationSlotMutationResult:
        logger.info(
            "log_handler.start user_id=%s plan_id=%s slot_id=%s request_id=%s",
            command.user_id,
            command.plan_id,
            command.slot_id,
            command.request_id,
        )
        async with self.uow as uow:
            plan, slot, replayed = await uow.meal_recommendation_plans.claim_slot_log(
                user_id=command.user_id,
                plan_id=command.plan_id,
                slot_id=command.slot_id,
                request_id=command.request_id,
            )
            selected = slot.selected
            logger.info(
                "log_handler.claimed user_id=%s plan_id=%s slot_id=%s "
                "request_id=%s replayed=%s slot_date=%s meal_type=%s "
                "catalog_meal_id=%s has_catalog_meal=%s logged_meal_id=%s "
                "skipped_at=%s",
                command.user_id,
                command.plan_id,
                command.slot_id,
                command.request_id,
                replayed,
                slot.slot_date,
                slot.meal_type,
                selected.catalog_meal_id if selected is not None else None,
                bool(selected is not None and selected.catalog_meal is not None),
                slot.logged_meal_id,
                slot.skipped_at,
            )
            if replayed:
                logger.info(
                    "log_handler.replay user_id=%s plan_id=%s slot_id=%s "
                    "request_id=%s logged_meal_id=%s",
                    command.user_id,
                    command.plan_id,
                    command.slot_id,
                    command.request_id,
                    slot.logged_meal_id,
                )
                return PersistedMealRecommendationSlotMutationResult(
                    plan_id=plan.id,
                    user_id=plan.user_id,
                    slot=slot,
                )
            meal = await self.materializer.materialize(uow, plan=plan, slot=slot)
            logger.info(
                "log_handler.materialized user_id=%s plan_id=%s slot_id=%s "
                "request_id=%s meal_id=%s",
                command.user_id,
                command.plan_id,
                command.slot_id,
                command.request_id,
                meal.meal_id,
            )
            result = await uow.meal_recommendation_plans.finalize_slot_logged(
                user_id=command.user_id,
                plan_id=command.plan_id,
                slot_id=command.slot_id,
                request_id=command.request_id,
                meal_id=meal.meal_id,
            )
            logger.info(
                "log_handler.finalized user_id=%s plan_id=%s slot_id=%s "
                "request_id=%s meal_id=%s result_logged_meal_id=%s",
                command.user_id,
                command.plan_id,
                command.slot_id,
                command.request_id,
                meal.meal_id,
                result.slot.logged_meal_id,
            )
            return result
