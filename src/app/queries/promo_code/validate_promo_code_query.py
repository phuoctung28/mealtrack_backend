"""Query and error type for validating a promo code before purchase."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidatePromoCodeQuery:
    code: str
    user_id: str
    current_offering_id: Optional[str] = None


class PromoCodeValidationError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
