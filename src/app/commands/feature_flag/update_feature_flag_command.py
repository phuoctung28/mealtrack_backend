"""Command to update a feature flag."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateFeatureFlagCommand:
    name: str
    enabled: Optional[bool] = None
    description: Optional[str] = None
