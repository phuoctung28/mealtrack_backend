"""Handler for resolving a user's effective timezone."""

from src.app.events.base import EventHandler, handles
from src.app.queries.user import GetUserTimezoneQuery
from src.domain.utils.timezone_utils import resolve_user_timezone_async


@handles(GetUserTimezoneQuery)
class GetUserTimezoneQueryHandler(EventHandler[GetUserTimezoneQuery, str]):
    """Resolve timezone with the same precedence as budget/macros queries."""

    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def handle(self, query: GetUserTimezoneQuery) -> str:
        async with self.uow_factory() as uow:
            return await resolve_user_timezone_async(
                query.user_id,
                uow,
                query.header_timezone,
            )
