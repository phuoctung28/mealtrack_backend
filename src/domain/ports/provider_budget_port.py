"""Port for shared external-provider request budgets."""

from typing import Protocol


class ProviderBudgetPort(Protocol):
    """Reserve one request from a provider's shared rolling-window budget."""

    async def acquire(self, namespace: str, limit: int) -> bool:
        """Return false when the shared budget is unavailable or exhausted."""
