"""Query handler — validate a referral code: existence, self-referral, already-referred checks."""

import logging
from typing import Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.referral.validate_referral_code_query import (
    ValidateCodeResult,
    ValidateReferralCodeQuery,
)
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.referral_repository_async import AsyncReferralRepository

logger = logging.getLogger(__name__)


@handles(ValidateReferralCodeQuery)
class ValidateReferralCodeQueryHandler(
    EventHandler[ValidateReferralCodeQuery, ValidateCodeResult]
):
    def __init__(self, uow: Optional[AsyncUnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, query: ValidateReferralCodeQuery) -> ValidateCodeResult:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            repo = AsyncReferralRepository(uow.session)

            code = await repo.get_code_by_code(query.code)
            if not code:
                return ValidateCodeResult(valid=False, error="invalid_code")

            if code.user_id == query.user_id:
                return ValidateCodeResult(valid=False, error="self_referral")

            existing = await repo.get_conversion_by_referred_user(query.user_id)
            if existing:
                return ValidateCodeResult(valid=False, error="already_referred")

            # Fetch referrer's first name for personalised UI copy
            referrer_name = await repo.get_user_first_name(code.user_id)

            return ValidateCodeResult(
                valid=True,
                referrer_name=referrer_name,
                discount_monthly=199000,
                discount_annual=499000,
            )
