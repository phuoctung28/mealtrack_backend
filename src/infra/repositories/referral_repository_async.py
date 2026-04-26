"""Async repository for referral system persistence — codes, conversions, wallets, payouts."""

import random
import string
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.referral import (
    PayoutRequest,
    ReferralCode,
    ReferralConversion,
    ReferralWallet,
)
from src.infra.database.models.user.user import User


class AsyncReferralRepository:
    """Async repository for referral data. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # === Code Operations ===

    async def get_code_by_user_id(self, user_id: str) -> Optional[ReferralCode]:
        result = await self.session.execute(
            select(ReferralCode).where(ReferralCode.user_id == user_id)
        )
        return result.scalars().first()

    async def get_code_by_code(self, code: str) -> Optional[ReferralCode]:
        result = await self.session.execute(
            select(ReferralCode).where(ReferralCode.code == code.upper())
        )
        return result.scalars().first()

    async def create_code(self, user_id: str) -> ReferralCode:
        code = await self._generate_unique_code()
        referral_code = ReferralCode(
            user_id=user_id,
            code=code,
            created_at=utc_now(),
        )
        self.session.add(referral_code)
        await self.session.flush()
        return referral_code

    async def _generate_unique_code(self) -> str:
        for _ in range(10):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not await self.get_code_by_code(code):
                return code
        raise RuntimeError("Failed to generate unique referral code after 10 attempts")

    # === Conversion Operations ===

    async def get_conversion_by_referred_user(
        self, user_id: str
    ) -> Optional[ReferralConversion]:
        result = await self.session.execute(
            select(ReferralConversion).where(
                ReferralConversion.referred_user_id == user_id
            )
        )
        return result.scalars().first()

    async def get_conversions_by_referrer(
        self, user_id: str
    ) -> List[ReferralConversion]:
        result = await self.session.execute(
            select(ReferralConversion)
            .where(ReferralConversion.referrer_user_id == user_id)
            .order_by(ReferralConversion.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_conversion(
        self,
        referrer_user_id: str,
        referred_user_id: str,
        code: str,
        discount: int,
    ) -> ReferralConversion:
        conversion = ReferralConversion(
            referrer_user_id=referrer_user_id,
            referred_user_id=referred_user_id,
            code_used=code.upper(),
            status="pending",
            discount_applied=discount,
            commission_amount=50000,
        )
        self.session.add(conversion)
        await self.session.flush()
        return conversion

    # === Wallet Operations ===

    async def get_or_create_wallet(self, user_id: str) -> ReferralWallet:
        result = await self.session.execute(
            select(ReferralWallet).where(ReferralWallet.user_id == user_id)
        )
        wallet = result.scalars().first()
        if not wallet:
            wallet = ReferralWallet(
                user_id=user_id,
                balance=0,
                total_earned=0,
                total_revoked=0,
                total_withdrawn=0,
                updated_at=utc_now(),
            )
            self.session.add(wallet)
            await self.session.flush()
        return wallet

    async def credit_wallet(self, user_id: str, amount: int) -> ReferralWallet:
        wallet = await self.get_or_create_wallet(user_id)
        wallet.balance += amount
        wallet.total_earned += amount
        wallet.updated_at = utc_now()
        return wallet

    async def revoke_from_wallet(self, user_id: str, amount: int) -> ReferralWallet:
        wallet = await self.get_or_create_wallet(user_id)
        wallet.balance = max(0, wallet.balance - amount)
        wallet.total_revoked += amount
        wallet.updated_at = utc_now()
        return wallet

    # === Payout Operations ===

    async def get_pending_payout(self, user_id: str) -> Optional[PayoutRequest]:
        result = await self.session.execute(
            select(PayoutRequest).where(
                PayoutRequest.user_id == user_id,
                PayoutRequest.status.in_(["pending", "processing"]),
            )
        )
        return result.scalars().first()

    async def create_payout_request(
        self, user_id: str, amount: int, method: str, details: dict
    ) -> PayoutRequest:
        request = PayoutRequest(
            user_id=user_id,
            amount=amount,
            payment_method=method,
            payment_details=details,
            status="pending",
            requested_at=utc_now(),
        )
        self.session.add(request)
        await self.session.flush()
        return request

    # === User Operations ===

    async def get_user_first_name(self, user_id: str) -> str:
        result = await self.session.execute(
            select(User.first_name, User.display_name).where(User.id == user_id)
        )
        row = result.first()
        if not row:
            return "Friend"
        raw = row.first_name or row.display_name or ""
        return raw.split()[0] if raw.strip() else "Friend"
