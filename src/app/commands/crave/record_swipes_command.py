from dataclasses import dataclass, field

from src.app.events.base import Command


@dataclass
class SwipeItem:
    catalog_meal_id: str
    direction: str
    position: int | None = None
    dwell_ms: int | None = None
    meal_type: str | None = None


@dataclass
class RecordSwipesCommand(Command):
    user_id: str
    swipes: list[SwipeItem] = field(default_factory=list)
    deck_id: str | None = None
