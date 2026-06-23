"""
JSON extraction utilities for AI responses.

Shim: the canonical implementation lives in src.infra.ai.json_extract.
Re-exports for backward compatibility; no callers remain after Phase 2c migration.
"""

from src.infra.ai.json_extract import _clean_json as clean_json_content  # noqa: F401
from src.infra.ai.json_extract import (
    _close_structures as close_json_structures,
)
from src.infra.ai.json_extract import (  # noqa: F401
    _find_last_valid_position as find_last_valid_json_position,
)
from src.infra.ai.json_extract import extract_json  # noqa: F401

__all__ = [
    "extract_json",
    "clean_json_content",
    "find_last_valid_json_position",
    "close_json_structures",
]
