"""Command dataclass for recording a referred user's code application (pre-purchase)."""

from dataclasses import dataclass


@dataclass
class ApplyReferralCodeCommand:
    user_id: str
    code: str
    discount_applied: int  # 199000 (monthly) or 499000 (annual)
