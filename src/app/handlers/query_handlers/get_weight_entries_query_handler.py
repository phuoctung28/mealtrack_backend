"""Handler for getting weight entries."""

import logging
from typing import Dict, Any, List

from src.app.events.base import EventHandler, handles
from src.app.queries.weight import GetWeightEntriesQuery
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(GetWeightEntriesQuery)
class GetWeightEntriesQueryHandler(EventHandler[GetWeightEntriesQuery, Dict[str, Any]]):
    """Handler for getting user's weight entries."""

    async def handle(self, query: GetWeightEntriesQuery) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            entries = await uow.weight_entries.find_by_user(
                query.user_id, query.limit, query.offset
            )

            return {
                "entries": [
                    {
                        "id": e.id,
                        "weight_kg": e.weight_kg,
                        "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                    }
                    for e in entries
                ],
                "count": len(entries),
            }
