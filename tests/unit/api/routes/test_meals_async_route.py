"""
Unit tests for async meal analysis route behavior.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import Response
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request

from src.api.routes.v1.meals import analyze_meal_image_immediate
from src.infra.config.settings import settings
from src.infra.database.uow import UnitOfWork
from tests.fixtures.mock_image_store import MockImageStore


class _FakeQueue:
    def __init__(self) -> None:
        self.enqueued_payload = None

    async def enqueue(self, payload):
        self.enqueued_payload = payload
        return "job-test-123"


@pytest.mark.asyncio
async def test_async_meal_analysis_enqueues_job_and_returns_accepted(
    monkeypatch,
    test_session,
    sample_user,
):
    fake_queue = _FakeQueue()
    image_store = MockImageStore()

    original_flag = settings.MEAL_IMAGE_ASYNC_ENABLED
    settings.MEAL_IMAGE_ASYNC_ENABLED = True

    try:
        monkeypatch.setattr("src.api.routes.v1.meals.get_job_queue", lambda: fake_queue)
        monkeypatch.setattr(
            "src.api.routes.v1.meals.UnitOfWork",
            lambda *args, **kwargs: UnitOfWork(session=test_session),
        )

        scope = {"type": "http", "headers": []}
        request = Request(scope)
        response = Response()
        upload_file = UploadFile(
            filename="meal.jpg",
            file=BytesIO(b"fake-image-bytes"),
            headers=Headers({"content-type": "image/jpeg"}),
        )

        result = await analyze_meal_image_immediate(
            request=request,
            response=response,
            file=upload_file,
            user_id=sample_user.id,
            target_date=None,
            user_description=None,
            sync=False,
            image_store=image_store,
        )
    finally:
        settings.MEAL_IMAGE_ASYNC_ENABLED = original_flag

    assert response.status_code == 202
    assert result.job_id == "job-test-123"
    assert result.status == "queued"
    assert result.poll_url == "/v1/jobs/job-test-123"
    assert result.meal_id is not None

    assert fake_queue.enqueued_payload is not None
    payload = fake_queue.enqueued_payload.payload
    assert payload["meal_id"] == result.meal_id
    assert payload["content_type"] == "image/jpeg"
    assert payload["image_id"] is not None

