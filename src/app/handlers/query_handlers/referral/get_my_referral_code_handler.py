"""Query handler — get or lazily create the authenticated user's referral code."""
import logging

from src.app.queries.referral.get_my_referral_code_query import (
    GetMyReferralCodeQuery,
    ReferralCodeResult,
)
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.referral_repository import ReferralRepository

logger = logging.getLogger(__name__)


class GetMyReferralCodeQueryHandler:
    async def handle(self, query: GetMyReferralCodeQuery) -> ReferralCodeResult:
        async with AsyncUnitOfWork() as uow:
            repo = ReferralRepository(uow.session)

            code = await repo.get_code_by_user_id(query.user_id)
            if not code:
                code = await repo.create_code(query.user_id)
                logger.info("Created new referral code for user %s", query.user_id)

            return ReferralCodeResult(
                code=code.code,
                created_at=code.created_at.isoformat(),
            )
