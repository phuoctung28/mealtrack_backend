"""Small helpers for running async code in sync RQ tasks."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine from a sync context."""
    return asyncio.run(coro)

