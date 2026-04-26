"""Query to get all feature flags."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class GetFeatureFlagsQuery:
    pass


@dataclass
class FeatureFlagsResult:
    flags: Dict[str, bool]
    updated_at: datetime
