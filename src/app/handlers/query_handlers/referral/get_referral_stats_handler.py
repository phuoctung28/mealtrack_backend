"""Query handler — return the user's referral code, wallet balance, and conversion history."""

import logging
from typing import List

from sqlalchemy import select

from src.app.queries.referral.get_referral_stats_query import (
    GetReferralStatsQuery,
    ReferralConversionDTO,
    ReferralStatsResult,
)
from src.infra.database.models.user.user import User
from src.infra.repositories.referral_repository import ReferralRepository

logger = logging.getLogger(__name__)


class GetReferralStatsQueryHandler:
    def handle(self, query: GetReferralStatsQuery, uow) -> ReferralStatsResult:
        repo = ReferralRepository(uow.session)

        # Ensure code exists (lazy-create so stats endpoint never errors on first call)
        code = repo.get_code_by_user_id(query.user_id)
        if not code:
            code = repo.create_code(query.user_id)
            uow.commit()

        wallet = repo.get_or_create_wallet(query.user_id)
        conversions = repo.get_conversions_by_referrer(query.user_id)
        pending_payout = repo.get_pending_payout(query.user_id)

        total_converted = sum(1 for c in conversions if c.status == "converted")

        conversion_dtos: List[ReferralConversionDTO] = []
        for conv in conversions:
            referred_name = self._get_first_name(uow, conv.referred_user_id)
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

    def _get_first_name(self, uow, user_id: str) -> str:
        result = uow.session.execute(
            select(User.first_name, User.display_name).where(User.id == user_id)
        )
        row = result.first()
        if not row:
            return "Friend"
        raw = row.first_name or row.display_name or ""
        return raw.split()[0] if raw.strip() else "Friend"
