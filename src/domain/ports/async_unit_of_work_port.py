"""Abstract port for the async Unit of Work."""
from abc import ABC, abstractmethod
from typing import Any


class AsyncUnitOfWorkPort(ABC):
    """Async context manager interface for database transactions."""

    @abstractmethod
    async def __aenter__(self) -> "AsyncUnitOfWorkPort":
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass

    @abstractmethod
    async def refresh(self, obj: Any) -> None:
        pass
