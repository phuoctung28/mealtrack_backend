"""Async repository for promo code system — validation and redemption tracking."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.promo_code import PromoCode, PromoCodeRedemption


class PromoCodeRepository:
    """Async SQLAlchemy promo code repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code: str) -> Optional[PromoCode]:
        result = await self.session.execute(
            select(PromoCode).where(PromoCode.code == code.strip().upper())
        )
        return result.scalars().first()

    async def get_redemption(
        self, promo_code_id: str, user_id: str
    ) -> Optional[PromoCodeRedemption]:
        result = await self.session.execute(
            select(PromoCodeRedemption).where(
                PromoCodeRedemption.promo_code_id == promo_code_id,
                PromoCodeRedemption.user_id == user_id,
            )
        )
        return result.scalars().first()

    async def create_redemption(
        self, promo_code: PromoCode, user_id: str
    ) -> PromoCodeRedemption:
        promo_code.current_uses += 1
        redemption = PromoCodeRedemption(
            promo_code_id=promo_code.id,
            user_id=user_id,
            redeemed_at=utc_now(),
        )
        self.session.add(redemption)
        return redemption
