"""Client capability discovery endpoints."""

from fastapi import APIRouter

from src.app.services.durable_write_service import RETENTION_DAYS

router = APIRouter(prefix="/v1/capabilities", tags=["Capabilities"])


@router.get("/durable-writes")
async def get_durable_write_capabilities() -> dict:
    """Advertise which mutations support exact Idempotency-Key replay."""
    return {
        "retention_days": RETENTION_DAYS,
        "actions": {
            "manual_meal_create": {
                "supported": True,
                "header": "Idempotency-Key",
                "exact_replay": True,
            },
            "weight_sync": {
                "supported": False,
                "reason": "client_entry_id_mapping_pending",
            },
        },
    }
