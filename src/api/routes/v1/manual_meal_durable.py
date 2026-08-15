"""Idempotency helpers for POST /v1/meals/manual."""

from __future__ import annotations

from typing import Any

from src.api.schemas.request.meal_requests import CreateManualMealFromFoodsRequest
from src.infra.services.durable_write_service import canonicalize_fingerprint


def manual_meal_fingerprint(payload: CreateManualMealFromFoodsRequest) -> str:
    """Fingerprint logical write fields only (ignore edit-only metadata)."""
    items: list[dict[str, Any]] = []
    for item in payload.items:
        nutrition = None
        if item.custom_nutrition is not None:
            nutrition = item.custom_nutrition.model_dump(mode="json")
        items.append(
            {
                "fdc_id": item.fdc_id,
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "custom_nutrition": nutrition,
            }
        )
    body: dict[str, Any] = {
        "dish_name": payload.dish_name,
        "meal_type": payload.meal_type,
        "target_date": payload.target_date,
        "source": payload.source,
        "emoji": payload.emoji,
        "items": items,
    }
    return canonicalize_fingerprint(body)
