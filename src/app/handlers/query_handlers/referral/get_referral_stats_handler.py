"""Query handler — return the user's referral code, wallet balance, and conversion history."""

import logging
from typing import List, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.referral.get_referral_stats_query import (
    GetReferralStatsQuery,
    ReferralConversionDTO,
    ReferralStatsResult,
)
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.referral_repository_async import AsyncReferralRepository

logger = logging.getLogger(__name__)


@handles(GetReferralStatsQuery)
class GetReferralStatsQueryHandler(
    EventHandler[GetReferralStatsQuery, ReferralStatsResult]
):
    def __init__(self, uow: Optional[AsyncUnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, query: GetReferralStatsQuery) -> ReferralStatsResult:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            repo = AsyncReferralRepository(uow.session)

            # Ensure code exists (lazy-create so stats endpoint never errors on first call)
            code = await repo.get_code_by_user_id(query.user_id)
            if not code:
                code = await repo.create_code(query.user_id)

            wallet = await repo.get_or_create_wallet(query.user_id)
            conversions = await repo.get_conversions_by_referrer(query.user_id)
            pending_payout = await repo.get_pending_payout(query.user_id)

            total_converted = sum(1 for c in conversions if c.status == "converted")

            conversion_dtos: List[ReferralConversionDTO] = []
            for conv in conversions:
                referred_name = await repo.get_user_first_name(conv.referred_user_id)
                conversion_dtos.append(
                    ReferralConversionDTO(
                        referred_name=referred_name,
                        status=conv.status,
                        amount=conv.commission_amount,
                        date=conv.created_at.isoformat(),
                    )
                )

            return ReferralStatsResult(
                code=code.code,
                wallet_balance=wallet.balance,
                total_earned=wallet.total_earned,
                total_withdrawn=wallet.total_withdrawn,
                total_invited=len(conversions),
                total_converted=total_converted,
                conversions=conversion_dtos,
                has_pending_payout=pending_payout is not None,
            )
