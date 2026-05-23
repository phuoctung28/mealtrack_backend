"""Abstract port for hydration persistence operations."""

from abc import ABC, abstractmethod
from datetime import date

from src.domain.model.hydration import HydrationEntry


class HydrationRepositoryPort(ABC):
    """Port interface for hydration log persistence operations."""

    @abstractmethod
    async def save(self, entry: HydrationEntry) -> HydrationEntry:
        """
        Persist a hydration entry.

        Args:
            entry: The hydration entry to save.

        Returns:
            The saved hydration entry.
        """
        ...

    @abstractmethod
    async def find_by_id(
        self, user_id: str, entry_id: str
    ) -> HydrationEntry | None:
        """
        Find a hydration entry by user and entry ID.

        Args:
            user_id: The owning user's UUID string.
            entry_id: The entry's UUID string.

        Returns:
            The hydration entry if found, None otherwise.
        """
        ...

    @abstractmethod
    async def find_by_date(
        self, user_id: str, target_date: date, user_timezone: str
    ) -> list[HydrationEntry]:
        """
        Return all non-deleted entries for a user on a given local date.

        Args:
            user_id: The owning user's UUID string.
            target_date: Local calendar date to filter by.
            user_timezone: IANA timezone identifier for date boundary conversion.

        Returns:
            List of hydration entries for the specified date.
        """
        ...

    @abstractmethod
    async def soft_delete(self, user_id: str, entry_id: str) -> bool:
        """
        Soft-delete a hydration entry by setting is_deleted=True.

        Args:
            user_id: The owning user's UUID string.
            entry_id: The entry's UUID string.

        Returns:
            True if the entry was found and marked deleted, False otherwise.
        """
        ...

    @abstractmethod
    async def sum_credited_ml_by_date_range(
        self, user_id: str, start_date: date, end_date: date, user_timezone: str
    ) -> dict[date, int]:
        """
        Return total credited_ml per local calendar date for a date range.

        Args:
            user_id: The owning user's UUID string.
            start_date: First local date (inclusive).
            end_date: Last local date (inclusive).
            user_timezone: IANA timezone identifier.

        Returns:
            Mapping of local date → total credited_ml (dates with no entries are absent).
        """
        ...

    @abstractmethod
    async def sum_credited_ml_for_date(
        self, user_id: str, target_date: date, user_timezone: str
    ) -> int:
        """
        Sum credited_ml for all non-deleted entries on a given local date.

        Args:
            user_id: The owning user's UUID string.
            target_date: Local calendar date to aggregate.
            user_timezone: IANA timezone identifier for date boundary conversion.

        Returns:
            Total credited ml for the date (0 if no entries).
        """
        ...
