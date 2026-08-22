"""Query and result dataclass for retrieving (or lazily creating) the user's referral code."""

from dataclasses import dataclass


@dataclass
class GetMyReferralCodeQuery:
    user_id: str


@dataclass
class ReferralCodeResult:
    code: str
    created_at: str
