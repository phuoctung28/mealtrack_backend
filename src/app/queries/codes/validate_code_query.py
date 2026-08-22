"""Query and error type for the unified code validation endpoint."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidateCodeQuery:
    code: str
    user_id: str
    current_offering_id: Optional[str] = None


class CodeValidationError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
