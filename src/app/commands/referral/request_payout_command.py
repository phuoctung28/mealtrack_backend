"""Command dataclass for initiating a referral wallet withdrawal request."""
from dataclasses import dataclass
from typing import Dict


@dataclass
class RequestPayoutCommand:
    user_id: str
    amount: int
    payment_method: str  # 'momo' or 'bank'
    payment_details: Dict  # {'phone': '...'} or {'bank': '...', 'account': '...'}
