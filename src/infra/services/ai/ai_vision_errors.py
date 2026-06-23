"""Classified vision analysis failure types."""
from enum import Enum


class AIVisionFailureKind(Enum):
    transient = "transient"              # 5xx, provider unavailable — retry/fallback allowed
    timeout = "timeout"                  # request timed out — fallback allowed, budget-gated retry
    rate_limit = "rate_limit"            # 429 — fallback allowed, no immediate same-model retry
    schema_validation = "schema_validation"  # valid JSON but wrong shape — next provider only
    json_parse = "json_parse"            # unparseable response — next provider only
    no_food = "no_food"                  # no food detected — no retry, no fallback
    unknown = "unknown"                  # unclassified — next provider if available


class AIVisionError(Exception):
    """Vision analysis failure with classified kind.

    Raised by providers and the model manager so callers can route
    retry/fallback behavior without parsing raw exception messages.
    """

    def __init__(
        self,
        message: str,
        kind: AIVisionFailureKind,
        provider: str = "",
        model: str = "",
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.provider = provider
        self.model = model
