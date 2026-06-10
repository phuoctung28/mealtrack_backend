"""Process-wide BackgroundTaskManager singleton for the API layer.

Lives in api/dependencies so routes and main can access it without
crossing the api→infra direct-import boundary.
"""

from src.infra.event_bus import BackgroundTaskManager

_instance: BackgroundTaskManager | None = None


def create_task_manager() -> BackgroundTaskManager:
    """Factory — called once during lifespan startup."""
    return BackgroundTaskManager()


def get_task_manager() -> BackgroundTaskManager:
    """Return the process-wide instance.

    Raises RuntimeError if called before lifespan startup completes.
    """
    if _instance is None:
        raise RuntimeError(
            "BackgroundTaskManager not initialised. "
            "Ensure lifespan startup has completed before spawning tasks."
        )
    return _instance


def set_task_manager(manager: BackgroundTaskManager) -> None:
    """Register the process-wide instance. Called once during lifespan startup."""
    global _instance
    _instance = manager


def clear_task_manager() -> None:
    """Reset the singleton. Used in tests to guarantee isolation."""
    global _instance
    _instance = None
