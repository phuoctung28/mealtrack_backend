from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.infra.config.settings import settings
from src.infra.database.uow import UnitOfWork


client = TestClient(app)


@pytest.mark.unit
def test_get_meal_image_upload_signature_success(monkeypatch: pytest.MonkeyPatch):
    original_cloud_name = settings.CLOUDINARY_CLOUD_NAME
    original_key = settings.CLOUDINARY_API_KEY
    original_secret = settings.CLOUDINARY_API_SECRET
    settings.CLOUDINARY_CLOUD_NAME = "demo"
    settings.CLOUDINARY_API_KEY = "demo-key"
    settings.CLOUDINARY_API_SECRET = "demo-secret"

    try:
        from src.infra.adapters import cloudinary_signature_service as sig_module

        monkeypatch.setattr(
            sig_module.cloudinary.utils,
            "api_sign_request",
            lambda params_to_sign, api_secret: "signed-value",
        )

        response = client.post("/v1/meals/image/upload-signature")
    finally:
        settings.CLOUDINARY_CLOUD_NAME = original_cloud_name
        settings.CLOUDINARY_API_KEY = original_key
        settings.CLOUDINARY_API_SECRET = original_secret

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["cloud_name"] == "demo"
    assert data["api_key"] == "demo-key"
    assert data["signature"] == "signed-value"
    assert "timestamp" in data
    assert "folder" in data


@pytest.mark.unit
def test_analyze_meal_image_from_upload_enqueues_job(monkeypatch: pytest.MonkeyPatch, test_session):
    class FakeQueue:
        def __init__(self):
            self.enqueued = None

        async def enqueue(self, payload):
            self.enqueued = payload
            return "job-123"

    fake_queue = FakeQueue()

    original_async_flag = settings.MEAL_IMAGE_ASYNC_ENABLED
    settings.MEAL_IMAGE_ASYNC_ENABLED = True

    def fake_get_job_queue():
        return fake_queue

    from src.api.routes.v1 import meals as meals_module

    monkeypatch.setattr(meals_module, "get_job_queue", fake_get_job_queue)
    monkeypatch.setattr(
        meals_module,
        "UnitOfWork",
        lambda *args, **kwargs: UnitOfWork(session=test_session),
    )

    try:
        user_id = str(uuid4())
        # Bypass auth dependency by injecting header used by dev_auth_bypass
        headers = {"Authorization": "Bearer dev-token"}
        payload = {
            "public_id": "mealtrack/sample-public-id",
            "secure_url": "https://res.cloudinary.com/demo/image/upload/v123/mealtrack/sample-public-id.jpg",
            "content_type": "image/jpeg",
            "target_date": datetime.utcnow().date().strftime("%Y-%m-%d"),
            "user_description": "grilled chicken and rice",
        }
        response = client.post(
            "/v1/meals/image/analyze-from-upload",
            json=payload,
            headers=headers,
        )
    finally:
        settings.MEAL_IMAGE_ASYNC_ENABLED = original_async_flag

    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()
    assert body["job_id"] == "job-123"
    assert body["status"] == "queued"
    assert body["poll_url"] == "/v1/jobs/job-123"
    assert body["meal_id"] is not None

    assert fake_queue.enqueued is not None
    job_payload = fake_queue.enqueued
    assert job_payload.job_type == "meal_image_analysis"
    assert job_payload.payload["meal_id"] == body["meal_id"]
    assert job_payload.payload["image_id"] == "mealtrack/sample-public-id"
    assert job_payload.payload["content_type"] == "image/jpeg"

