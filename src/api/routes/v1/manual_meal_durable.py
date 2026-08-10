"""Idempotency helpers for POST /v1/meals/manual."""

from __future__ import annotations

from typing import Any

from src.api.schemas.request.meal_requests import CreateManualMealFromFoodsRequest
from src.infra.services.durable_write_service import canonicalize_fingerprint


def manual_meal_fingerprint(payload: CreateManualMealFromFoodsRequest) -> str:
    """Fingerprint only logical write fields (ignore transport metadata)."""
    body: dict[str, Any] = payload.model_dump(mode="json")
    return canonicalize_fingerprint(body)
