"""Command dataclass for recording a promo code redemption after successful purchase."""
from dataclasses import dataclass


@dataclass
class RedeemPromoCodeCommand:
    code: str
    user_id: str
