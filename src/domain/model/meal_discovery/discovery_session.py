"""Session model tracking shown meals during discovery browsing."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.domain.utils.timezone_utils import utc_now


@dataclass
class DiscoverySession:
    """
    Tracks which meals a user has already seen during a discovery session.

    Sessions expire after 4 hours. Shown meal names are used to exclude
    duplicates when generating subsequent batches.
    """

    id: str
    user_id: str
    shown_meal_ids: List[str] = field(default_factory=list)
    shown_meal_names: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None  # Set to created_at + 4h on creation
