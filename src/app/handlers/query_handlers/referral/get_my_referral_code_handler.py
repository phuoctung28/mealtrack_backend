"""Query handler — get or lazily create the authenticated user's referral code."""

import logging

from src.app.queries.referral.get_my_referral_code_query import (
    GetMyReferralCodeQuery,
    ReferralCodeResult,
)
from src.infra.repositories.referral_repository import ReferralRepository

logger = logging.getLogger(__name__)


class GetMyReferralCodeQueryHandler:
    def handle(self, query: GetMyReferralCodeQuery, uow) -> ReferralCodeResult:
        repo = ReferralRepository(uow.session)

        code = repo.get_code_by_user_id(query.user_id)
        if not code:
            code = repo.create_code(query.user_id)
            uow.commit()
            logger.info("Created new referral code for user %s", query.user_id)

        return ReferralCodeResult(
            code=code.code,
            created_at=code.created_at.isoformat(),
        )
