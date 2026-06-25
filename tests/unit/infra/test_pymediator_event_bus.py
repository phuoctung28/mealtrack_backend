import logging
from dataclasses import dataclass

import pytest

from src.api.exceptions import ResourceNotFoundException
from src.domain.events.base import EventHandler, Query
from src.domain.exceptions.ai_exceptions import AIUnavailableError
from src.infra.event_bus.pymediator_event_bus import PyMediatorEventBus


@dataclass
class _MissingMealQuery(Query):
    meal_id: str


@dataclass
class _CrashingQuery(Query):
    name: str


@dataclass
class _AIUnavailableQuery(Query):
    purpose: str


class _MissingMealHandler(EventHandler[_MissingMealQuery, None]):
    async def handle(self, event: _MissingMealQuery) -> None:
        raise ResourceNotFoundException(f"Meal with ID {event.meal_id} not found")


class _AIUnavailableHandler(EventHandler[_AIUnavailableQuery, None]):
    async def handle(self, event: _AIUnavailableQuery) -> None:
        raise AIUnavailableError(
            f"All vision models failed for {event.purpose}",
            attempted_models=["gpt-5.4-mini-2026-03-17", "gpt-5.4-mini-2026-03-17"],
            last_error="504 DEADLINE_EXCEEDED",
        )


class _CrashingHandler(EventHandler[_CrashingQuery, None]):
    async def handle(self, event: _CrashingQuery) -> None:
        raise RuntimeError(f"Unexpected failure for {event.name}")


@pytest.mark.asyncio
async def test_expected_application_exception_is_not_logged_as_error(caplog):
    bus = PyMediatorEventBus()
    bus.register_handler(_MissingMealQuery, _MissingMealHandler())

    with caplog.at_level(
        logging.DEBUG,
        logger="src.infra.event_bus.pymediator_event_bus",
    ):
        with pytest.raises(ResourceNotFoundException):
            await bus.send(_MissingMealQuery(meal_id="meal-1"))

    assert not [
        record
        for record in caplog.records
        if record.levelno >= logging.ERROR and "Error handling" in record.message
    ]
    assert any(
        record.levelno == logging.DEBUG
        and "Application exception handling _MissingMealQuery" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_ai_unavailable_exception_is_not_logged_as_error(caplog):
    bus = PyMediatorEventBus()
    bus.register_handler(_AIUnavailableQuery, _AIUnavailableHandler())

    with caplog.at_level(
        logging.DEBUG,
        logger="src.infra.event_bus.pymediator_event_bus",
    ):
        with pytest.raises(AIUnavailableError):
            await bus.send(_AIUnavailableQuery(purpose="meal_scan"))

    assert not [
        record
        for record in caplog.records
        if record.levelno >= logging.ERROR and "Error handling" in record.message
    ]
    assert any(
        record.levelno == logging.DEBUG
        and "Application exception handling _AIUnavailableQuery" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_unexpected_exception_is_logged_as_error(caplog):
    bus = PyMediatorEventBus()
    bus.register_handler(_CrashingQuery, _CrashingHandler())

    with caplog.at_level(
        logging.ERROR,
        logger="src.infra.event_bus.pymediator_event_bus",
    ):
        with pytest.raises(RuntimeError):
            await bus.send(_CrashingQuery(name="test"))

    assert any(
        record.levelno == logging.ERROR
        and "Error handling _CrashingQuery" in record.message
        for record in caplog.records
    )
