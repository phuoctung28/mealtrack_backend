"""Prefer-slot then standalone materialization for catalog meal logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.app.commands.meal_catalog import LogCatalogMealCommand
from src.app.services.recommended_meal_materialization_service import (
    RecommendedMealMaterializationService,
)
from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationAlreadyLoggedError,
    MealRecommendationTerminalStateError,
)
from src.domain.model.meal import Meal
from src.domain.model.meal_recommendation import CatalogMeal


@dataclass(frozen=True)
class LogCatalogMealResult:
    meal_id: str
    catalog_meal_id: str
    logged_via: str
    plan_id: str | None
    slot_id: str | None
    meal_date: date
    meal_type: str
    meal: Meal

    @property
    def logged_meal_id(self) -> str:
        return self.meal_id

    def to_replay_payload(self) -> dict[str, str | None]:
        return {
            "meal_id": self.meal_id,
            "catalog_meal_id": self.catalog_meal_id,
            "logged_via": self.logged_via,
            "plan_id": self.plan_id,
            "slot_id": self.slot_id,
            "logged_meal_id": self.meal_id,
            "meal_date": self.meal_date.isoformat(),
            "meal_type": self.meal_type,
        }


class CatalogMealLogService:
    """Resolve prefer-slot vs standalone catalog logging."""

    def __init__(
        self,
        materializer: RecommendedMealMaterializationService | None = None,
    ) -> None:
        self._materializer = materializer or RecommendedMealMaterializationService()

    async def execute(
        self,
        uow,
        command: LogCatalogMealCommand,
        catalog_meal: CatalogMeal,
    ) -> LogCatalogMealResult:
        match = await uow.meal_recommendation_plans.find_logable_slot_for_catalog_meal(
            user_id=command.user_id,
            catalog_meal_id=command.catalog_meal_id,
            slot_date=command.meal_date,
            meal_type=command.meal_type,
        )
        if match is not None:
            try:
                return await self._log_via_slot(
                    uow,
                    command=command,
                    catalog_meal=catalog_meal,
                    plan_id=match[0],
                    slot_id=match[1],
                )
            except (
                MealRecommendationAlreadyLoggedError,
                MealRecommendationTerminalStateError,
            ):
                pass
        return await self._log_standalone(uow, command, catalog_meal)

    async def _log_via_slot(
        self,
        uow,
        *,
        command: LogCatalogMealCommand,
        catalog_meal: CatalogMeal,
        plan_id: str,
        slot_id: str,
    ) -> LogCatalogMealResult:
        plan, slot, replayed = await uow.meal_recommendation_plans.claim_slot_log(
            user_id=command.user_id,
            plan_id=plan_id,
            slot_id=slot_id,
            request_id=command.request_id,
        )
        if replayed and slot.logged_meal_id:
            meal = await uow.meals.find_by_id(slot.logged_meal_id)
            if meal is None:
                raise MealRecommendationAlreadyLoggedError
            return self._result(
                meal=meal,
                catalog_meal_id=command.catalog_meal_id,
                logged_via="slot",
                plan_id=plan_id,
                slot_id=slot_id,
                meal_date=command.meal_date,
                meal_type=command.meal_type,
            )
        meal = await self._materializer.materialize(uow, plan=plan, slot=slot)
        await uow.meal_recommendation_plans.finalize_slot_logged(
            user_id=command.user_id,
            plan_id=plan_id,
            slot_id=slot_id,
            request_id=command.request_id,
            meal_id=meal.meal_id,
        )
        return self._result(
            meal=meal,
            catalog_meal_id=catalog_meal.id,
            logged_via="slot",
            plan_id=plan_id,
            slot_id=slot_id,
            meal_date=command.meal_date,
            meal_type=command.meal_type,
        )

    async def _log_standalone(
        self,
        uow,
        command: LogCatalogMealCommand,
        catalog_meal: CatalogMeal,
    ) -> LogCatalogMealResult:
        meal = await self._materializer.materialize_from_catalog(
            uow,
            user_id=command.user_id,
            catalog_meal=catalog_meal,
            meal_date=command.meal_date,
            meal_type=command.meal_type,
            timezone=command.timezone,
        )
        return self._result(
            meal=meal,
            catalog_meal_id=catalog_meal.id,
            logged_via="catalog",
            plan_id=None,
            slot_id=None,
            meal_date=command.meal_date,
            meal_type=command.meal_type,
        )

    @staticmethod
    def _result(
        *,
        meal: Meal,
        catalog_meal_id: str,
        logged_via: str,
        plan_id: str | None,
        slot_id: str | None,
        meal_date: date,
        meal_type: str,
    ) -> LogCatalogMealResult:
        return LogCatalogMealResult(
            meal_id=meal.meal_id,
            catalog_meal_id=catalog_meal_id,
            logged_via=logged_via,
            plan_id=plan_id,
            slot_id=slot_id,
            meal_date=meal_date,
            meal_type=meal_type,
            meal=meal,
        )
