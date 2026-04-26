"""Query handler — get or lazily create the authenticated user's referral code."""

import logging
from typing import Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.referral.get_my_referral_code_query import (
    GetMyReferralCodeQuery,
    ReferralCodeResult,
)
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.referral_repository_async import AsyncReferralRepository

logger = logging.getLogger(__name__)


@handles(GetMyReferralCodeQuery)
class GetMyReferralCodeQueryHandler(
    EventHandler[GetMyReferralCodeQuery, ReferralCodeResult]
):
    def __init__(self, uow: Optional[AsyncUnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, query: GetMyReferralCodeQuery) -> ReferralCodeResult:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            repo = AsyncReferralRepository(uow.session)

            code = await repo.get_code_by_user_id(query.user_id)
            if not code:
                code = await repo.create_code(query.user_id)
                logger.info("Created new referral code for user %s", query.user_id)

            return ReferralCodeResult(
                code=code.code,
                created_at=code.created_at.isoformat(),
            )
