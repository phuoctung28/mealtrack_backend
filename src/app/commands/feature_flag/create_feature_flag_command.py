"""Command to create a feature flag."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateFeatureFlagCommand:
    name: str
    enabled: bool = False
    description: Optional[str] = None
