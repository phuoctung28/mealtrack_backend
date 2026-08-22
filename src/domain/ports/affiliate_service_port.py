"""Abstract port for affiliate code validation via nutree-affiliate internal API."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AffiliateCodeValidationResult:
    active: bool
    affiliate_id: str | None = None
    code_id: str | None = None
    display_name: str | None = None
    partner_type: str | None = None


class AffiliateServicePort(ABC):
    @abstractmethod
    async def validate_code(self, code: str) -> AffiliateCodeValidationResult:
        """Call nutree-affiliate to check if a code is active and return affiliate metadata."""
