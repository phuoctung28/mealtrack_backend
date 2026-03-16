from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.model.job_queue import JobPayload
from src.worker.job_router import JobRouter


class _EventBusStub:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def send(self, command: Any) -> Any:  # pragma: no cover - trivial passthrough
        self.sent.append(command)
        return None


@pytest.mark.asyncio
async def test_meal_image_analysis_routed_to_upload_command():
    router = JobRouter()
    bus = _EventBusStub()

    payload = JobPayload(
        job_type="meal_image_analysis",
        user_id="user-1",
        payload={
            "file_contents": b"fake-bytes",
            "content_type": "image/jpeg",
            "language": "en",
            "user_description": "test meal",
        },
    )

    with patch(
        "src.worker.job_router.get_configured_event_bus",
        return_value=bus,
    ):
        await router.handle(payload)

    assert len(bus.sent) == 1
    command = bus.sent[0]
    # Import here to avoid unused import when tests are not run
    from src.app.commands.meal import UploadMealImageImmediatelyCommand  # noqa: WPS433

    assert isinstance(command, UploadMealImageImmediatelyCommand)
    assert command.user_id == "user-1"
    assert command.file_contents == b"fake-bytes"
    assert command.content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_meal_image_analysis_preuploaded_payload_routed_to_upload_command():
    router = JobRouter()
    bus = _EventBusStub()

    payload = JobPayload(
        job_type="meal_image_analysis",
        user_id="user-1",
        payload={
            "meal_id": "8d03f5fe-8be0-45ef-946f-7c7e4fd4cf6a",
            "image_id": "9fb42c60-bc03-4d7e-9630-f06d09e8d22a",
            "image_url": "mock://images/9fb42c60-bc03-4d7e-9630-f06d09e8d22a",
            "content_type": "image/jpeg",
            "target_date": "2026-03-14",
        },
    )

    with patch(
        "src.worker.job_router.get_configured_event_bus",
        return_value=bus,
    ):
        await router.handle(payload)

    assert len(bus.sent) == 1
    command = bus.sent[0]
    from src.app.commands.meal import UploadMealImageImmediatelyCommand  # noqa: WPS433

    assert isinstance(command, UploadMealImageImmediatelyCommand)
    assert command.meal_id == "8d03f5fe-8be0-45ef-946f-7c7e4fd4cf6a"
    assert command.image_id == "9fb42c60-bc03-4d7e-9630-f06d09e8d22a"
    assert command.file_contents is None
    assert command.content_type == "image/jpeg"
    assert command.target_date is not None


@pytest.mark.asyncio
async def test_meal_suggestions_routed_to_generate_command():
    router = JobRouter()
    bus = _EventBusStub()

    payload = JobPayload(
        job_type="meal_suggestions",
        user_id="user-2",
        payload={
            "meal_type": "lunch",
            "meal_portion_type": "main",
            "ingredients": ["chicken", "rice"],
            "language": "en",
            "servings": 2,
        },
    )

    with patch(
        "src.worker.job_router.get_configured_event_bus",
        return_value=bus,
    ):
        await router.handle(payload)

    assert len(bus.sent) == 1
    command = bus.sent[0]
    from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand  # noqa: WPS433

    assert isinstance(command, GenerateMealSuggestionsCommand)
    assert command.user_id == "user-2"
    assert command.meal_type == "lunch"
    assert command.meal_portion_type == "main"
    assert command.ingredients == ["chicken", "rice"]


@pytest.mark.asyncio
async def test_unsupported_job_type_raises_value_error():
    router = JobRouter()
    payload = JobPayload(
        job_type="unknown_type",
        user_id="user-3",
        payload={},
    )

    with patch(
        "src.worker.job_router.get_configured_event_bus",
        return_value=_EventBusStub(),
    ):
        with pytest.raises(ValueError):
            await router.handle(payload)

