"""Read a cached progress recap for one timeline window."""

from dataclasses import dataclass
from datetime import date

from src.app.events.base import Query
from src.domain.services.progress_recap_facts import HORIZONS


@dataclass
class GetProgressRecapQuery(Query):
    user_id: str
    horizon: str
    start_date: date | None = None
    end_date: date | None = None
    header_timezone: str | None = None
    locale: str = "en"

    def __post_init__(self) -> None:
        horizon = (self.horizon or "").strip().lower()
        if horizon not in HORIZONS:
            raise ValueError("horizon must be day, week, month, or year")
        self.horizon = horizon
        token = (self.locale or "en").split(",")[0].split(";")[0].strip()
        self.locale = (token.split("-")[0] or "en")[:8]
