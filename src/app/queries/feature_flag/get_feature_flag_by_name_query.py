"""Query to get a feature flag by name."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GetFeatureFlagByNameQuery:
    name: str


@dataclass
class FeatureFlagResult:
    name: str
    enabled: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
