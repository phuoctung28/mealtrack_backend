"""Runtime capability declarations for mobile contract rollouts."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from src.infra.database.uow_async import AsyncUnitOfWork

router = APIRouter(prefix="/v1/capabilities", tags=["capabilities"])

_REQUIRED_DURABLE_WRITE_COLUMNS = {
    "food_item": {
        "source_kind",
        "source_food_id",
        "nutrition_contract_version",
        "source_snapshot",
    },
    "meal_write_operation": {
        "user_id",
        "operation",
        "idempotency_key",
        "request_fingerprint",
        "status",
        "lease_owner",
        "lease_generation",
        "lease_expires_at",
        "target_meal_id",
        "response",
    },
}


def _durable_write_schema_is_ready(rows) -> bool:
    available: dict[str, set[str]] = {}
    for table_name, column_name in rows:
        available.setdefault(table_name, set()).add(column_name)
    return all(
        required.issubset(available.get(table_name, set()))
        for table_name, required in _REQUIRED_DURABLE_WRITE_COLUMNS.items()
    )


@router.get("/durable-writes")
async def durable_write_capabilities() -> dict[str, object]:
    """Advertise v2 writes only when their durable storage is migrated."""
    try:
        async with AsyncUnitOfWork() as uow:
            session = uow.session
            if session is None:
                raise RuntimeError("database session is unavailable")
            result = await session.execute(
                text(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND (
                        (table_name = 'food_item' AND column_name IN (
                          'source_kind', 'source_food_id',
                          'nutrition_contract_version', 'source_snapshot'
                        ))
                        OR (table_name = 'meal_write_operation' AND column_name IN (
                          'user_id', 'operation', 'idempotency_key',
                          'request_fingerprint', 'status', 'lease_owner',
                          'lease_generation', 'lease_expires_at',
                          'target_meal_id', 'response'
                        ))
                      )
                    """
                )
            )
            if not _durable_write_schema_is_ready(result.all()):
                raise RuntimeError("durable write schema is incomplete")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "DURABLE_WRITES_UNAVAILABLE",
                "message": "Durable write storage is not available",
            },
        ) from exc

    return {
        "durable_writes": True,
        "nutrition_contract_version": 2,
        "operations": ["create_manual_meal", "edit_meal"],
    }
