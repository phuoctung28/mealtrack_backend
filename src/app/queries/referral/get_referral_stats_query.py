"""Query and result dataclasses for retrieving a user's full referral stats and wallet."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class GetReferralStatsQuery:
    user_id: str


@dataclass
class ReferralConversionDTO:
    referred_name: str  # First name only for privacy
    status: str
    amount: int
    date: str


@dataclass
class ReferralStatsResult:
    code: str
    wallet_balance: int
    total_earned: int
    total_withdrawn: int
    total_invited: int
    total_converted: int
    conversions: List[ReferralConversionDTO] = field(default_factory=list)
    has_pending_payout: bool = False
