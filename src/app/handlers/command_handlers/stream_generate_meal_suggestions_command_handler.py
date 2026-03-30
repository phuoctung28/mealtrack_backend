"""
StreamGenerateMealSuggestionsCommandHandler - stream meal generation events.
"""
import json
import logging
from typing import AsyncGenerator

from src.api.mappers.meal_suggestion_mapper import to_meal_suggestion_response
from src.app.commands.meal_suggestion.stream_generate_meal_suggestions_command import (
    StreamGenerateMealSuggestionsCommand,
)
from src.app.events.base import EventHandler, handles
from src.domain.services.meal_suggestion.suggestion_orchestration_service import (
    SuggestionOrchestrationService,
)

logger = logging.getLogger(__name__)


@handles(StreamGenerateMealSuggestionsCommand)
class StreamGenerateMealSuggestionsCommandHandler(
    EventHandler[StreamGenerateMealSuggestionsCommand, AsyncGenerator[str, None]]
):
    """Handler for streaming meal suggestion generation as SSE payloads."""

    def __init__(self, service: SuggestionOrchestrationService):
        self.service = service

    async def handle(
        self, command: StreamGenerateMealSuggestionsCommand
    ) -> AsyncGenerator[str, None]:
        async def sse_generator() -> AsyncGenerator[str, None]:
            try:
                async for event in self.service.stream_suggestions(
                    user_id=command.user_id,
                    meal_type=command.meal_type,
                    meal_portion_type=command.meal_portion_type,
                    ingredients=command.ingredients,
                    cooking_time_minutes=command.time_available_minutes,
                    session_id=command.session_id,
                    language=command.language,
                    servings=command.servings,
                    cooking_equipment=command.cooking_equipment,
                    cuisine_region=command.cuisine_region,
                    calorie_target_override=command.calorie_target,
                    protein_target=command.protein_target,
                    carbs_target=command.carbs_target,
                    fat_target=command.fat_target,
                ):
                    event_name = event.get("event", "message")
                    data = event.get("data", {})

                    if event_name == "meal_detail" and "suggestion" in data:
                        suggestion = data["suggestion"]
                        data = {
                            "index": data.get("index"),
                            "suggestion": to_meal_suggestion_response(suggestion).model_dump(),
                        }

                    yield f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error("Streaming meal suggestions failed: %s", e)
                error_data = {"message": "Failed to generate meal suggestions"}
                yield f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        return sse_generator()
