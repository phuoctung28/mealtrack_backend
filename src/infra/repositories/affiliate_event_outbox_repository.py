"""Repository for affiliate_event_outbox — enqueue and claim outbox rows."""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.affiliate_event_outbox import AffiliateEventOutbox

MAX_ATTEMPTS = 5


class AffiliateEventOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
    ) -> AffiliateEventOutbox | None:
        """Insert an outbox row.  Returns None on duplicate event_id (idempotent)."""
        row = AffiliateEventOutbox(
            id=str(uuid.uuid4()),
            event_id=event_id or str(uuid.uuid4()),
            event_type=event_type,
            payload=payload,
            status="pending",
            attempts=0,
            next_attempt_at=utc_now(),
            created_at=utc_now(),
        )
        try:
            # Nested transaction (savepoint) so a duplicate only rolls back this
            # insert, never the outer UoW transaction the caller is already in.
            async with self._session.begin_nested():
                self._session.add(row)
            return row
        except IntegrityError:
            return None

    async def claim_pending(self, limit: int = 50) -> list[AffiliateEventOutbox]:
        """Claim up to `limit` pending rows that are due for delivery."""
        now = utc_now()
        stmt = (
            select(AffiliateEventOutbox)
            .where(
                AffiliateEventOutbox.status == "pending",
                AffiliateEventOutbox.next_attempt_at <= now,
                AffiliateEventOutbox.attempts < MAX_ATTEMPTS,
            )
            .order_by(AffiliateEventOutbox.next_attempt_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        if rows:
            ids = [r.id for r in rows]
            await self._session.execute(
                update(AffiliateEventOutbox)
                .where(AffiliateEventOutbox.id.in_(ids))
                .values(locked_at=now)
            )
        return rows

    async def mark_sent(self, row_id: str) -> None:
        await self._session.execute(
            update(AffiliateEventOutbox)
            .where(AffiliateEventOutbox.id == row_id)
            .values(status="sent", sent_at=utc_now(), locked_at=None)
        )

    async def mark_failed(self, row_id: str, error: str) -> bool:
        """Update failure state.  Returns True if row is now permanently failed."""
        result = await self._session.execute(
            select(AffiliateEventOutbox).where(AffiliateEventOutbox.id == row_id)
        )
        row = result.scalars().first()
        if row is None:
            return False
        row.attempts += 1
        row.last_error = error
        row.locked_at = None
        if row.attempts >= MAX_ATTEMPTS:
            row.status = "failed"
            return True
        # Exponential back-off: 1m, 5m, 30m, 2h, ...
        backoff_minutes = [1, 5, 30, 120, 480]
        delay = backoff_minutes[min(row.attempts - 1, len(backoff_minutes) - 1)]
        row.next_attempt_at = datetime.now(UTC) + timedelta(minutes=delay)
        return False
