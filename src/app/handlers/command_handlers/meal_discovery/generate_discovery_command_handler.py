"""Handler for GenerateDiscoveryCommand — delegates to DiscoveryOrchestrationService."""
import logging
from typing import List, Tuple

from src.app.commands.meal_discovery import GenerateDiscoveryCommand
from src.domain.model.meal_discovery import DiscoveryMeal, DiscoverySession
from src.domain.services.meal_discovery.discovery_orchestration_service import (
    DiscoveryOrchestrationService,
)

logger = logging.getLogger(__name__)


class GenerateDiscoveryCommandHandler:
    """
    Handles GenerateDiscoveryCommand.
    Receives the orchestration service as a constructor dependency (singleton-safe).
    """

    def __init__(self, discovery_service: DiscoveryOrchestrationService):
        self._service = discovery_service

    async def handle(
        self, command: GenerateDiscoveryCommand
    ) -> Tuple[DiscoverySession, List[DiscoveryMeal]]:
        """Delegate to orchestration service and return (session, meals)."""
        return await self._service.generate(
            user_id=command.user_id,
            meal_type=command.meal_type,
            cuisine_filter=command.cuisine_filter,
            cooking_time=command.cooking_time,
            calorie_level=command.calorie_level,
            macro_focus=command.macro_focus,
            exclude_ids=command.exclude_ids,
            language=command.language,
        )
