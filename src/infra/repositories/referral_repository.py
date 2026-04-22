"""Repository for referral system persistence — codes, conversions, wallets, payouts."""
import random
import string
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.referral import (
    PayoutRequest,
    ReferralCode,
    ReferralConversion,
    ReferralWallet,
)


class ReferralRepository:
    def __init__(self, db: Session):
        self.db = db

    # === Code Operations ===

    def get_code_by_user_id(self, user_id: str) -> Optional[ReferralCode]:
        return (
            self.db.query(ReferralCode)
            .filter(ReferralCode.user_id == user_id)
            .first()
        )

    def get_code_by_code(self, code: str) -> Optional[ReferralCode]:
        return (
            self.db.query(ReferralCode)
            .filter(ReferralCode.code == code.upper())
            .first()
        )

    def create_code(self, user_id: str) -> ReferralCode:
        code = self._generate_unique_code()
        referral_code = ReferralCode(
            user_id=user_id,
            code=code,
            created_at=utc_now(),
        )
        self.db.add(referral_code)
        return referral_code

    def _generate_unique_code(self) -> str:
        for _ in range(10):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not self.get_code_by_code(code):
                return code
        raise RuntimeError("Failed to generate unique referral code after 10 attempts")

    # === Conversion Operations ===

    def get_conversion_by_referred_user(self, user_id: str) -> Optional[ReferralConversion]:
        return (
            self.db.query(ReferralConversion)
            .filter(ReferralConversion.referred_user_id == user_id)
            .first()
        )

    def get_conversions_by_referrer(self, user_id: str) -> List[ReferralConversion]:
        return (
            self.db.query(ReferralConversion)
            .filter(ReferralConversion.referrer_user_id == user_id)
            .order_by(ReferralConversion.created_at.desc())
            .all()
        )

    def create_conversion(
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
        self.db.add(conversion)
        return conversion

    # === Wallet Operations ===

    def get_or_create_wallet(self, user_id: str) -> ReferralWallet:
        wallet = (
            self.db.query(ReferralWallet)
            .filter(ReferralWallet.user_id == user_id)
            .first()
        )
        if not wallet:
            wallet = ReferralWallet(
                user_id=user_id,
                balance=0,
                total_earned=0,
                total_revoked=0,
                total_withdrawn=0,
                updated_at=utc_now(),
            )
            self.db.add(wallet)
        return wallet

    def credit_wallet(self, user_id: str, amount: int) -> ReferralWallet:
        wallet = self.get_or_create_wallet(user_id)
        wallet.balance += amount
        wallet.total_earned += amount
        wallet.updated_at = utc_now()
        return wallet

    def revoke_from_wallet(self, user_id: str, amount: int) -> ReferralWallet:
        wallet = self.get_or_create_wallet(user_id)
        wallet.balance = max(0, wallet.balance - amount)
        wallet.total_revoked += amount
        wallet.updated_at = utc_now()
        return wallet

    # === Payout Operations ===

    def create_payout_request(
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
        self.db.add(request)
        return request

    def get_pending_payout(self, user_id: str) -> Optional[PayoutRequest]:
        return (
            self.db.query(PayoutRequest)
            .filter(
                PayoutRequest.user_id == user_id,
                PayoutRequest.status.in_(["pending", "processing"]),
            )
            .first()
        )
