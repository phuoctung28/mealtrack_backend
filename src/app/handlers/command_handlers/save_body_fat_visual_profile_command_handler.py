"""Append visual body-fat profile selections without altering measured metrics."""

from src.app.commands.user.save_body_fat_visual_profile_command import (
    SaveBodyFatVisualProfileCommand,
)
from src.app.events.base import EventHandler, handles
from src.infra.database.models.user.body_fat_visual_profile import BodyFatVisualProfile
from src.infra.database.uow_async import AsyncUnitOfWork


@handles(SaveBodyFatVisualProfileCommand)
class SaveBodyFatVisualProfileCommandHandler(
    EventHandler[SaveBodyFatVisualProfileCommand, None]
):
    """Persist each selection as a new record to preserve selection history."""

    async def handle(self, command: SaveBodyFatVisualProfileCommand) -> None:
        async with AsyncUnitOfWork() as uow:
            uow.session.add(
                BodyFatVisualProfile(
                    user_id=command.user_id,
                    schema_version=command.schema_version,
                    range_catalog_version=command.range_catalog_version,
                    sex_at_selection=command.sex_at_selection,
                    current_range_id=command.current_range_id,
                    target_range_id=command.target_range_id,
                )
            )
