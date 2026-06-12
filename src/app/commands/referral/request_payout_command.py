"""Command dataclass for initiating a referral wallet withdrawal request."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RequestPayoutCommand:
    user_id: str
    amount: int
    payment_method: str  # 'momo' or 'bank'
    payment_details: dict[
        str, Any
    ]  # {'phone': '...'} or {'bank': '...', 'account': '...'}
