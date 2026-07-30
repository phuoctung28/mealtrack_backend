"""Port for append-only visual body-fat profile persistence."""

from abc import ABC, abstractmethod

from src.domain.model.user.body_fat_visual import BodyFatVisualProfileSelection


class BodyFatVisualProfileRepositoryPort(ABC):
    """Persistence operations for visual body-fat selection history."""

    @abstractmethod
    async def append(self, selection: BodyFatVisualProfileSelection) -> None:
        """Append a selection without modifying prior history."""

    @abstractmethod
    async def find_history_by_user(
        self, user_id: str
    ) -> list[BodyFatVisualProfileSelection]:
        """Return one user's selection history in stable chronological order."""
