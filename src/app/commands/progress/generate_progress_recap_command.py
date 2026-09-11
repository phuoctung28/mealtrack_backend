"""Generate an AI progress recap for one timeline window."""

from dataclasses import dataclass
from datetime import date

from src.app.events.base import Command
from src.domain.services.progress_recap_facts import HORIZONS


@dataclass
class GenerateProgressRecapCommand(Command):
    user_id: str
    horizon: str
    start_date: date | None = None
    end_date: date | None = None
    header_timezone: str | None = None
    locale: str = "en"
    force: bool = False

    def __post_init__(self) -> None:
        horizon = (self.horizon or "").strip().lower()
        if horizon not in HORIZONS:
            raise ValueError("horizon must be day, week, month, or year")
        self.horizon = horizon
        self.locale = _locale(self.locale)


def _locale(value: str) -> str:
    token = (value or "en").split(",")[0].split(";")[0].strip()
    return (token.split("-")[0] or "en")[:8]
