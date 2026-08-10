"""Lookup and persist exact-replay durable mutation responses."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.durable_write_record import DurableWriteRecordORM
from src.infra.database.uow_async import AsyncUnitOfWork

RETENTION_DAYS = 14
MANUAL_MEAL_CREATE_ACTION = "manual_meal_create"


class DurableWriteConflictError(Exception):
    """Same idempotency key was reused with a different request fingerprint."""


@dataclass(frozen=True)
class DurableWriteRecord:
    request_fingerprint: str
    response_status_code: int
    response_body: dict[str, Any]
    resource_id: str | None


def canonicalize_fingerprint(payload: Any) -> str:
    """SHA-256 of canonical JSON (sorted keys, compact separators)."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalize_idempotency_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = raw.strip()
    if not key:
        return None
    if len(key) > 160:
        raise ValueError("Idempotency-Key must be 160 characters or fewer")
    return key


def _to_record(row: DurableWriteRecordORM) -> DurableWriteRecord:
    return DurableWriteRecord(
        request_fingerprint=row.request_fingerprint,
        response_status_code=row.response_status_code,
        response_body=json.loads(row.response_body_json),
        resource_id=row.resource_id,
    )


async def get_durable_write(
    *,
    user_id: str,
    action: str,
    idempotency_key: str,
) -> DurableWriteRecord | None:
    async with AsyncUnitOfWork() as uow:
        row = await _fetch(uow, user_id, action, idempotency_key)
        if row is None or row.expires_at < utc_now():
            return None
        return _to_record(row)


async def resolve_or_conflict(
    *,
    user_id: str,
    action: str,
    idempotency_key: str,
    request_fingerprint: str,
) -> DurableWriteRecord | None:
    existing = await get_durable_write(
        user_id=user_id,
        action=action,
        idempotency_key=idempotency_key,
    )
    if existing is None:
        return None
    if existing.request_fingerprint != request_fingerprint:
        raise DurableWriteConflictError
    return existing


async def save_durable_write(
    *,
    user_id: str,
    action: str,
    idempotency_key: str,
    request_fingerprint: str,
    response_status_code: int,
    response_body: dict[str, Any],
    resource_id: str | None = None,
) -> DurableWriteRecord:
    body_json = json.dumps(response_body, default=str, separators=(",", ":"))
    now = utc_now()
    try:
        async with AsyncUnitOfWork() as uow:
            existing = await _fetch(uow, user_id, action, idempotency_key)
            if existing is not None:
                if existing.request_fingerprint != request_fingerprint:
                    raise DurableWriteConflictError
                if existing.expires_at >= now:
                    return _to_record(existing)
                existing.request_fingerprint = request_fingerprint
                existing.response_status_code = response_status_code
                existing.response_body_json = body_json
                existing.resource_id = resource_id
                existing.expires_at = now + timedelta(days=RETENTION_DAYS)
                return DurableWriteRecord(
                    request_fingerprint=request_fingerprint,
                    response_status_code=response_status_code,
                    response_body=response_body,
                    resource_id=resource_id,
                )
            uow.session.add(
                DurableWriteRecordORM(
                    user_id=user_id,
                    action=action,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    response_status_code=response_status_code,
                    response_body_json=body_json,
                    resource_id=resource_id,
                    expires_at=now + timedelta(days=RETENTION_DAYS),
                )
            )
    except IntegrityError as exc:
        raced = await get_durable_write(
            user_id=user_id,
            action=action,
            idempotency_key=idempotency_key,
        )
        if raced is None:
            raise DurableWriteConflictError from exc
        if raced.request_fingerprint != request_fingerprint:
            raise DurableWriteConflictError from exc
        return raced
    return DurableWriteRecord(
        request_fingerprint=request_fingerprint,
        response_status_code=response_status_code,
        response_body=response_body,
        resource_id=resource_id,
    )


async def _fetch(
    uow: AsyncUnitOfWork,
    user_id: str,
    action: str,
    key: str,
) -> DurableWriteRecordORM | None:
    result = await uow.session.execute(
        select(DurableWriteRecordORM).where(
            DurableWriteRecordORM.user_id == user_id,
            DurableWriteRecordORM.action == action,
            DurableWriteRecordORM.idempotency_key == key,
        )
    )
    return result.scalar_one_or_none()
