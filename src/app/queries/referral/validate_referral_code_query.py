"""Query and result dataclass for validating a referral code before it is applied."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidateReferralCodeQuery:
    code: str
    user_id: str  # The user attempting to use the code


@dataclass
class ValidateCodeResult:
    valid: bool
    error: Optional[str] = None
    referrer_name: Optional[str] = None
    discount_monthly: int = 199000
    discount_annual: int = 499000
