"""Module-level singleton for BackgroundTaskManager.

Both src/api/main.py (lifecycle owner) and route handlers can import from
here without creating circular imports between the api and infra layers.
"""

from src.infra.event_bus.background_task_manager import BackgroundTaskManager

_instance: BackgroundTaskManager | None = None


def get_task_manager() -> BackgroundTaskManager:
    """Return the process-wide BackgroundTaskManager instance.

    Raises RuntimeError if called before set_task_manager() (i.e. before
    lifespan startup completes).
    """
    if _instance is None:
        raise RuntimeError(
            "BackgroundTaskManager not initialised. "
            "Ensure lifespan startup has completed before spawning tasks."
        )
    return _instance


def set_task_manager(manager: BackgroundTaskManager) -> None:
    """Set the process-wide instance. Called once during lifespan startup."""
    global _instance
    _instance = manager


def clear_task_manager() -> None:
    """Reset the singleton. Used in tests to guarantee isolation."""
    global _instance
    _instance = None
