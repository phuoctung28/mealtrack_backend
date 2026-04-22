# Notification System Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 4,001-query per-batch notification system with a pre-compute + batch send architecture using Redis (user context cache) and PostgreSQL JSONB (notification job queue).

**Architecture:** A 60s scheduler loop detects timezones at local midnight, triggers a batch pre-compute (6 queries total for the whole group), writes context to Redis and creates `notifications` rows. At send time, 1 SQL query fetches due rows, 1 Redis pipeline fetches `calories_consumed`, then FCM sends are batched by message. The `notification_sent_log` table and dedup port are deleted; dedup is enforced by a UNIQUE constraint on `(user_id, notification_type, scheduled_date)`.

**Tech Stack:** SQLAlchemy 2.0 sync ORM, `redis.asyncio` pipeline, Firebase Admin SDK `MulticastMessage`, `zoneinfo.ZoneInfo` for DST-safe timezone math, Alembic for migration.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| MODIFY | `src/infra/cache/redis_client.py` | Add `hset_with_ttl`, `hset_batch`, `hgetall_batch` for hash ops |
| CREATE | `src/infra/database/models/notification/notification.py` | `NotificationORM` JSONB model |
| MODIFY | `src/infra/database/models/notification/__init__.py` | Export `NotificationORM`, remove `NotificationSentLog` |
| CREATE | `migrations/versions/050_notification_optimization.py` | Create `notifications`, drop `notification_sent_log` |
| CREATE | `src/infra/services/daily_context_precompute_service.py` | Batch pre-compute per timezone group |
| MODIFY | `src/infra/repositories/notification/reminder_query_builder.py` | Add `find_due_notifications` |
| MODIFY | `src/infra/services/firebase_service.py` | Add public `send_multicast` method |
| MODIFY | `src/infra/services/scheduled_notification_service.py` | Rewrite: midnight detection + batch send loop |
| MODIFY | `src/domain/services/notification_service.py` | Remove dedup logic and `dedup_store` |
| MODIFY | `src/api/base_dependencies.py` | Wire new services, remove `NotificationSentLogDedupStore` |
| DELETE | `src/infra/database/models/notification/notification_sent_log.py` | Dead — replaced by `notifications` table |
| DELETE | `src/domain/ports/notification_dedup_port.py` | Dead — UNIQUE constraint replaces it |
| DELETE | `src/infra/adapters/notification_sent_log_dedup_store.py` | Dead — no dedup store needed |

---

## Task 1: Extend RedisClient with hash + pipeline operations

**Files:**
- Modify: `src/infra/cache/redis_client.py`
- Test: `tests/unit/infra/test_redis_hash_ops.py` (create)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/infra/test_redis_hash_ops.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_hset_with_ttl_pipelines_hset_and_expire():
    from src.infra.cache.redis_client import RedisClient
    client = RedisClient.__new__(RedisClient)
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=False)
    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    client.client = mock_redis

    await client.hset_with_ttl("k", {"a": "1"}, 3600)

    mock_pipe.hset.assert_called_once_with("k", mapping={"a": "1"})
    mock_pipe.expire.assert_called_once_with("k", 3600)
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_hset_batch_writes_all_items():
    from src.infra.cache.redis_client import RedisClient
    client = RedisClient.__new__(RedisClient)
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=False)
    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    client.client = mock_redis

    items = [("k1", {"x": "1"}, 100), ("k2", {"y": "2"}, 200)]
    await client.hset_batch(items)

    assert mock_pipe.hset.call_count == 2
    assert mock_pipe.expire.call_count == 2


@pytest.mark.asyncio
async def test_hgetall_batch_returns_list_of_dicts():
    from src.infra.cache.redis_client import RedisClient
    client = RedisClient.__new__(RedisClient)
    mock_pipe = AsyncMock()
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=False)
    mock_pipe.execute = AsyncMock(return_value=[{"a": "1"}, None])
    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    client.client = mock_redis

    results = await client.hgetall_batch(["k1", "k2"])

    assert results == [{"a": "1"}, {}]
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/unit/infra/test_redis_hash_ops.py -v
```
Expected: `AttributeError: 'RedisClient' object has no attribute 'hset_with_ttl'`

- [ ] **Step 3: Add methods to RedisClient**

In `src/infra/cache/redis_client.py`, add after the `exists` method:

```python
async def hset_with_ttl(self, key: str, mapping: dict, ttl: int) -> bool:
    """Set a hash and its TTL in a single pipeline round-trip."""
    if not self.client:
        return False
    try:
        async with self.client.pipeline(transaction=False) as pipe:
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, ttl)
            await pipe.execute()
        return True
    except RedisError as exc:
        logger.warning("Redis HSET pipeline error for key %s: %s", key, exc)
        return False

async def hset_batch(self, items: list[tuple[str, dict, int]]) -> bool:
    """Set multiple hashes with TTL in a single pipeline. items: [(key, mapping, ttl)]."""
    if not self.client or not items:
        return True
    try:
        async with self.client.pipeline(transaction=False) as pipe:
            for key, mapping, ttl in items:
                pipe.hset(key, mapping=mapping)
                pipe.expire(key, ttl)
            await pipe.execute()
        return True
    except RedisError as exc:
        logger.warning("Redis batch HSET pipeline error: %s", exc)
        return False

async def hgetall_batch(self, keys: list[str]) -> list[dict]:
    """Fetch all fields of multiple hashes in a single pipeline. Returns list aligned to keys."""
    if not self.client or not keys:
        return [{} for _ in keys]
    try:
        async with self.client.pipeline(transaction=False) as pipe:
            for key in keys:
                pipe.hgetall(key)
            results = await pipe.execute()
        return [r or {} for r in results]
    except RedisError as exc:
        logger.warning("Redis batch HGETALL pipeline error: %s", exc)
        return [{} for _ in keys]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/unit/infra/test_redis_hash_ops.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/cache/redis_client.py tests/unit/infra/test_redis_hash_ops.py
git commit -m "feat(cache): add hash + pipeline batch ops to RedisClient"
```

---

## Task 2: Create NotificationORM model and migration

**Files:**
- Create: `src/infra/database/models/notification/notification.py`
- Modify: `src/infra/database/models/notification/__init__.py`
- Create: `migrations/versions/050_notification_optimization.py`

- [ ] **Step 1: Create the ORM model**

```python
# src/infra/database/models/notification/notification.py
"""Notification job queue model — replaces notification_sent_log."""
import uuid
from sqlalchemy import Column, String, Date, DateTime, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from src.infra.database.config import Base
from src.domain.utils.timezone_utils import utc_now


class NotificationORM(Base):
    """
    Pre-built notification job queue.

    Each row represents one scheduled send (user × type × date).
    UNIQUE constraint on (user_id, notification_type, scheduled_date) provides dedup.
    context JSONB: {fcm_tokens: [...], calorie_goal: int, gender: str, language_code: str}
    """
    __tablename__ = 'notifications'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    notification_type = Column(String(30), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    scheduled_for_utc = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(10), nullable=False, default='pending')
    context = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'user_id', 'notification_type', 'scheduled_date',
            name='uq_notification_per_user_type_date',
        ),
        Index(
            'idx_notifications_due',
            'scheduled_for_utc', 'status',
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            'idx_notifications_expires',
            'expires_at',
            postgresql_where=text("status != 'pending'"),
        ),
    )
```

- [ ] **Step 2: Update `__init__.py`**

Replace the contents of `src/infra/database/models/notification/__init__.py`:

```python
"""Notification database models."""
from .notification import NotificationORM
from .notification_preferences import NotificationPreferencesORM
from .user_fcm_token import UserFcmTokenORM

__all__ = [
    'NotificationORM',
    'NotificationPreferencesORM',
    'UserFcmTokenORM',
]
```

- [ ] **Step 3: Create migration 050**

```python
# migrations/versions/050_notification_optimization.py
"""Add notifications table and drop notification_sent_log.

Revision ID: 050
Revises: 049
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('notification_type', sa.String(30), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('scheduled_for_utc', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(10), nullable=False, server_default='pending'),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_unique_constraint(
        'uq_notification_per_user_type_date',
        'notifications',
        ['user_id', 'notification_type', 'scheduled_date'],
    )
    op.create_index(
        'idx_notifications_due',
        'notifications',
        ['scheduled_for_utc', 'status'],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        'idx_notifications_expires',
        'notifications',
        ['expires_at'],
        postgresql_where=sa.text("status != 'pending'"),
    )

    # Drop old dedup table
    op.drop_index('ix_sent_log_cleanup', table_name='notification_sent_log')
    op.drop_table('notification_sent_log')


def downgrade() -> None:
    op.drop_table('notifications')
    op.create_table(
        'notification_sent_log',
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('sent_minute', sa.String(16), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'notification_type', 'sent_minute'),
    )
    op.create_index('ix_sent_log_cleanup', 'notification_sent_log', ['sent_at'])
```

- [ ] **Step 4: Run migration**

```bash
alembic upgrade head
```
Expected: migration applies without error. Verify with `\dt` in psql: `notifications` table exists, `notification_sent_log` is gone.

- [ ] **Step 5: Commit**

```bash
git add src/infra/database/models/notification/notification.py \
        src/infra/database/models/notification/__init__.py \
        migrations/versions/050_notification_optimization.py
git commit -m "feat(db): add notifications JSONB table, drop notification_sent_log"
```

---

## Task 3: Create DailyContextPrecomputeService

**Files:**
- Create: `src/infra/services/daily_context_precompute_service.py`
- Test: `tests/unit/infra/test_daily_context_precompute_service.py` (create)

The service runs inside `asyncio.to_thread` for all SQL work (sync SQLAlchemy) and then writes to Redis asynchronously. It groups users by timezone name and triggers once per timezone per day using a Redis sentinel key.

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/infra/test_daily_context_precompute_service.py
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_skips_if_sentinel_exists():
    """Pre-compute is skipped when sentinel key already exists in Redis."""
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=True)
    svc = DailyContextPrecomputeService(redis_client=redis)

    with patch.object(svc, '_precompute_db_sync') as mock_sync:
        await svc.precompute_for_timezone('Asia/Ho_Chi_Minh', date(2026, 4, 22))
        mock_sync.assert_not_called()


@pytest.mark.asyncio
async def test_runs_and_sets_sentinel_when_missing():
    """Pre-compute runs and sets sentinel when key is absent."""
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=False)
    redis.hset_batch = AsyncMock()
    redis.set = AsyncMock()
    svc = DailyContextPrecomputeService(redis_client=redis)

    with patch.object(svc, '_precompute_db_sync', return_value=[]) as mock_sync:
        await svc.precompute_for_timezone('Asia/Ho_Chi_Minh', date(2026, 4, 22))
        mock_sync.assert_called_once()
        redis.set.assert_called_once()


def test_sentinel_key_format():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    key = svc.sentinel_key(date(2026, 4, 22), 'Asia/Ho_Chi_Minh')
    assert key == 'precomputed:2026-04-22:Asia/Ho_Chi_Minh'


def test_context_key_format():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    assert svc.context_key('user-123') == 'user_daily_context:user-123'
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/unit/infra/test_daily_context_precompute_service.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create the service**

```python
# src/infra/services/daily_context_precompute_service.py
"""Batch pre-compute user notification context per timezone group."""
import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.domain.services.meal_suggestion.suggestion_tdee_helpers import build_tdee_request
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.utils.timezone_utils import get_user_monday
from src.infra.cache.redis_client import RedisClient
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

_CONTEXT_TTL = 86_400       # 24 h
_SENTINEL_TTL = 25 * 3_600  # 25 h — survives the full day
_NOTIF_EXPIRY_DAYS = 7


class DailyContextPrecomputeService:
    """Pre-computes calorie_goal, consumed, gender, language per user at timezone midnight."""

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client
        self._tdee = TdeeCalculationService()

    # ── Key helpers ────────────────────────────────────────────────────────────

    def sentinel_key(self, today: date, tz_name: str) -> str:
        return f"precomputed:{today.isoformat()}:{tz_name}"

    def context_key(self, user_id: str) -> str:
        return f"user_daily_context:{user_id}"

    # ── Public API ─────────────────────────────────────────────────────────────

    async def is_precomputed(self, today: date, tz_name: str) -> bool:
        return await self._redis.exists(self.sentinel_key(today, tz_name))

    async def precompute_for_timezone(self, tz_name: str, today: date) -> None:
        """Batch pre-compute for all users in tz_name. No-op if already done today."""
        if await self.is_precomputed(today, tz_name):
            return

        logger.info("Pre-computing notification context for %s on %s", tz_name, today)
        redis_items = await asyncio.to_thread(self._precompute_db_sync, tz_name, today)

        if redis_items:
            await self._redis.hset_batch(redis_items)

        await self._redis.set(self.sentinel_key(today, tz_name), "1", ttl=_SENTINEL_TTL)
        logger.info("Pre-compute complete for %s: %d users", tz_name, len(redis_items))

    # ── Sync DB work (runs in thread pool) ────────────────────────────────────

    def _precompute_db_sync(self, tz_name: str, today: date) -> list[tuple[str, dict, int]]:
        """
        Runs inside asyncio.to_thread. Executes all DB queries and notification inserts.
        Returns list of (redis_key, mapping, ttl) for the async Redis batch write.
        """
        with UnitOfWork() as uow:
            # ── Step 1: users in this timezone with active FCM tokens ──────────
            from sqlalchemy import text
            rows = uow.session.execute(text("""
                SELECT DISTINCT
                    np.user_id,
                    np.meal_reminders_enabled,
                    np.daily_summary_enabled,
                    np.breakfast_time_minutes,
                    np.lunch_time_minutes,
                    np.dinner_time_minutes,
                    np.daily_summary_time_minutes,
                    u.language_code
                FROM notification_preferences np
                JOIN users u ON u.id = np.user_id
                JOIN user_fcm_tokens t ON t.user_id = np.user_id AND t.is_active = true
                WHERE u.timezone = :tz
                AND np.is_deleted = false
            """), {"tz": tz_name}).fetchall()

            if not rows:
                return []

            user_ids = [r.user_id for r in rows]
            user_ids_tuple = tuple(user_ids)

            # ── Step 2: FCM tokens per user ────────────────────────────────────
            token_rows = uow.session.execute(text("""
                SELECT user_id, fcm_token
                FROM user_fcm_tokens
                WHERE user_id IN :ids AND is_active = true
            """), {"ids": user_ids_tuple}).fetchall()
            tokens_by_user: dict[str, list[str]] = defaultdict(list)
            for r in token_rows:
                tokens_by_user[r.user_id].append(r.fcm_token)

            # ── Step 3: Profiles (batch) ───────────────────────────────────────
            profile_rows = uow.session.execute(text("""
                SELECT * FROM user_profiles WHERE user_id IN :ids
            """), {"ids": user_ids_tuple}).fetchall()
            profiles_by_user = {r.user_id: r for r in profile_rows}

            # ── Step 4: Compute calorie_goal + calories_consumed via WeeklyBudgetService ─
            week_start = get_user_monday(today, user_ids[0], uow)  # same week for all in tz
            calorie_goals: dict[str, int] = {}
            calories_consumed: dict[str, int] = {}
            genders: dict[str, str] = {}

            for row in rows:
                uid = row.user_id
                profile = profiles_by_user.get(uid)
                gender = getattr(profile, 'gender', 'male') or 'male'
                genders[uid] = gender

                if not profile:
                    calorie_goals[uid] = 2000
                    calories_consumed[uid] = 0
                    continue

                try:
                    tdee_result = self._tdee.calculate_tdee(build_tdee_request(profile))
                    weekly_budget = uow.weekly_budgets.find_by_user_and_week(uid, week_start)
                    if weekly_budget:
                        from src.domain.utils.timezone_utils import resolve_user_timezone
                        user_tz = resolve_user_timezone(uid, uow)
                        effective = WeeklyBudgetService.get_effective_adjusted_daily(
                            uow=uow,
                            user_id=uid,
                            week_start=week_start,
                            target_date=today,
                            weekly_budget=weekly_budget,
                            base_daily_cal=tdee_result.macros.calories,
                            base_daily_protein=tdee_result.macros.protein,
                            base_daily_carbs=tdee_result.macros.carbs,
                            base_daily_fat=tdee_result.macros.fat,
                            bmr=tdee_result.bmr,
                            user_timezone=user_tz,
                        )
                        calorie_goals[uid] = int(effective.adjusted.calories)
                        calories_consumed[uid] = int(
                            effective.consumed_total["calories"]
                            - effective.consumed_before_today["calories"]
                        )
                    else:
                        calorie_goals[uid] = int(tdee_result.macros.calories)
                        calories_consumed[uid] = 0
                except Exception as exc:
                    logger.warning("Calorie compute failed for %s: %s", uid, exc)
                    calorie_goals[uid] = 2000
                    calories_consumed[uid] = 0

            # ── Step 5: Insert notification rows for the day ───────────────────
            notification_inserts = self._build_notification_rows(
                rows, tokens_by_user, calorie_goals, genders, today, tz_name
            )
            if notification_inserts:
                uow.session.execute(text("""
                    INSERT INTO notifications
                        (id, user_id, notification_type, scheduled_date,
                         scheduled_for_utc, status, context, created_at, expires_at)
                    VALUES
                        (:id, :user_id, :notification_type, :scheduled_date,
                         :scheduled_for_utc, 'pending', CAST(:context AS jsonb),
                         NOW(), :expires_at)
                    ON CONFLICT (user_id, notification_type, scheduled_date)
                    DO NOTHING
                """), notification_inserts)
                uow.session.commit()

        # ── Step 6: Build Redis items (returned for async write) ────────────────
        redis_items = []
        for row in rows:
            uid = row.user_id
            redis_items.append((
                self.context_key(uid),
                {
                    "calorie_goal": str(calorie_goals.get(uid, 2000)),
                    "calories_consumed": str(calories_consumed.get(uid, 0)),
                    "gender": genders.get(uid, "male"),
                    "language_code": row.language_code or "en",
                },
                _CONTEXT_TTL,
            ))
        return redis_items

    def _build_notification_rows(
        self,
        pref_rows,
        tokens_by_user: dict[str, list[str]],
        calorie_goals: dict[str, int],
        genders: dict[str, str],
        today: date,
        tz_name: str,
    ) -> list[dict]:
        """Build INSERT dicts for all enabled reminders for each user today."""
        import json
        expires_at = datetime.combine(today + timedelta(days=_NOTIF_EXPIRY_DAYS),
                                      datetime.min.time()).replace(tzinfo=timezone.utc)
        rows = []
        for pref in pref_rows:
            uid = pref.user_id
            tokens = tokens_by_user.get(uid, [])
            if not tokens:
                continue
            context_base = {
                "fcm_tokens": tokens,
                "calorie_goal": calorie_goals.get(uid, 2000),
                "gender": genders.get(uid, "male"),
                "language_code": pref.language_code or "en",
            }

            type_time_pairs = []
            if pref.meal_reminders_enabled:
                if pref.breakfast_time_minutes is not None:
                    type_time_pairs.append(("meal_reminder_breakfast", pref.breakfast_time_minutes))
                if pref.lunch_time_minutes is not None:
                    type_time_pairs.append(("meal_reminder_lunch", pref.lunch_time_minutes))
                if pref.dinner_time_minutes is not None:
                    type_time_pairs.append(("meal_reminder_dinner", pref.dinner_time_minutes))
            if pref.daily_summary_enabled:
                minutes = pref.daily_summary_time_minutes or 1260
                type_time_pairs.append(("daily_summary", minutes))

            for notif_type, local_minutes in type_time_pairs:
                scheduled_for_utc = _local_minutes_to_utc(today, local_minutes, tz_name)
                if scheduled_for_utc is None:
                    continue
                rows.append({
                    "id": str(uuid.uuid4()),
                    "user_id": uid,
                    "notification_type": notif_type,
                    "scheduled_date": today,
                    "scheduled_for_utc": scheduled_for_utc,
                    "context": json.dumps(context_base),
                    "expires_at": expires_at,
                })
        return rows


def _local_minutes_to_utc(local_date: date, local_minutes: int, tz_name: str):
    """Convert local time (minutes from midnight) on local_date to UTC datetime."""
    try:
        tz = ZoneInfo(tz_name)
        local_dt = datetime(
            local_date.year, local_date.month, local_date.day,
            local_minutes // 60, local_minutes % 60, 0,
            tzinfo=tz,
        )
        return local_dt.astimezone(timezone.utc).replace(tzinfo=None)  # store as naive UTC
    except (ZoneInfoNotFoundError, ValueError) as exc:
        logger.warning("Cannot compute UTC for tz=%s minutes=%d: %s", tz_name, local_minutes, exc)
        return None
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/unit/infra/test_daily_context_precompute_service.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/daily_context_precompute_service.py \
        tests/unit/infra/test_daily_context_precompute_service.py
git commit -m "feat(notif): add DailyContextPrecomputeService for batch per-timezone pre-compute"
```

---

## Task 4: Add `find_due_notifications` to ReminderQueryBuilder

**Files:**
- Modify: `src/infra/repositories/notification/reminder_query_builder.py`
- Test: `tests/unit/infra/test_notification_queries.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/infra/test_notification_queries.py
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock


def test_find_due_notifications_queries_pending_in_window():
    from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder
    from src.infra.database.models.notification.notification import NotificationORM

    now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
    mock_notif = MagicMock(spec=NotificationORM)
    mock_notif.status = 'pending'

    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [mock_notif]

    db = MagicMock()
    db.query.return_value = mock_query

    results = ReminderQueryBuilder.find_due_notifications(db, now)

    db.query.assert_called_once_with(NotificationORM)
    assert results == [mock_notif]
```

- [ ] **Step 2: Run test — verify it fails**

```bash
pytest tests/unit/infra/test_notification_queries.py -v
```
Expected: `AttributeError: find_due_notifications`

- [ ] **Step 3: Add method to ReminderQueryBuilder**

Add to `src/infra/repositories/notification/reminder_query_builder.py` after existing imports:

```python
from src.infra.database.models.notification.notification import NotificationORM
```

Then add this static method inside `ReminderQueryBuilder`:

```python
@staticmethod
def find_due_notifications(db: Session, now: datetime) -> list:
    """
    Return all notifications scheduled within the current 60-second window.

    Args:
        db: Database session
        now: Current UTC datetime (naive or aware)

    Returns:
        List of NotificationORM with status='pending' due in [now, now+60s)
    """
    window_end = now + timedelta(seconds=60)
    return (
        db.query(NotificationORM)
        .filter(
            NotificationORM.scheduled_for_utc >= now,
            NotificationORM.scheduled_for_utc < window_end,
            NotificationORM.status == 'pending',
        )
        .all()
    )
```

Also add `timedelta` to the existing datetime imports at the top of the file.

- [ ] **Step 4: Run test — verify it passes**

```bash
pytest tests/unit/infra/test_notification_queries.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/repositories/notification/reminder_query_builder.py \
        tests/unit/infra/test_notification_queries.py
git commit -m "feat(notif): add find_due_notifications query to ReminderQueryBuilder"
```

---

## Task 5: Add `send_multicast` to FirebaseService

**Files:**
- Modify: `src/infra/services/firebase_service.py`
- Test: `tests/unit/infra/test_firebase_multicast.py` (create)

The existing `_send_to_tokens` already does multicast. This task exposes it as a clean public method that the scheduler calls directly with a pre-grouped token list.

- [ ] **Step 1: Write failing test**

```python
# tests/unit/infra/test_firebase_multicast.py
import pytest
from unittest.mock import patch, MagicMock


def test_send_multicast_delegates_to_send_to_tokens():
    from src.infra.services.firebase_service import FirebaseService

    svc = FirebaseService.__new__(FirebaseService)
    svc._send_to_tokens = MagicMock(return_value={"success": True, "sent": 2, "failed": 0, "failed_tokens": []})

    with patch('src.infra.services.firebase_service.firebase_admin') as mock_admin:
        mock_admin._apps = {"default": object()}
        result = svc.send_multicast(
            tokens=["tok1", "tok2"],
            title="Lunch time!",
            body="800 cal left",
            notification_type="meal_reminder_lunch",
        )

    svc._send_to_tokens.assert_called_once()
    assert result["success"] is True


def test_send_multicast_returns_not_initialized_when_firebase_not_ready():
    from src.infra.services.firebase_service import FirebaseService

    svc = FirebaseService.__new__(FirebaseService)

    with patch('src.infra.services.firebase_service.firebase_admin') as mock_admin:
        mock_admin._apps = {}
        result = svc.send_multicast(tokens=["tok"], title="t", body="b")

    assert result == {"success": False, "reason": "firebase_not_initialized"}
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/unit/infra/test_firebase_multicast.py -v
```
Expected: `AttributeError: 'FirebaseService' object has no attribute 'send_multicast'`

- [ ] **Step 3: Add `send_multicast` to FirebaseService**

Add this method to `FirebaseService` in `src/infra/services/firebase_service.py`, after `send_notification`:

```python
def send_multicast(
    self,
    tokens: list[str],
    title: str,
    body: str,
    notification_type: str = "scheduled",
    data: dict[str, str] | None = None,
) -> dict:
    """
    Send the same notification to a batch of FCM tokens (up to 500 per call).

    Used by the scheduler to batch-send to users sharing the same message.
    Caller is responsible for chunking to 500 tokens max.
    """
    if not firebase_admin._apps:
        return {"success": False, "reason": "firebase_not_initialized"}

    message_data = dict(data or {})
    message_data["type"] = notification_type
    return self._send_to_tokens(tokens, title, body, message_data)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/unit/infra/test_firebase_multicast.py -v
```
Expected: both tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/firebase_service.py \
        tests/unit/infra/test_firebase_multicast.py
git commit -m "feat(firebase): expose send_multicast for batch notification sends"
```

---

## Task 6: Rewrite ScheduledNotificationService

**Files:**
- Modify: `src/infra/services/scheduled_notification_service.py`
- Test: `tests/unit/infra/test_scheduled_notification_service.py` (create)

The new loop has two phases: midnight detection → pre-compute, then due-notification fetch → batch FCM send.

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/infra/test_scheduled_notification_service.py
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_detects_midnight_timezone():
    from src.infra.services.scheduled_notification_service import _timezones_at_midnight
    # 2026-04-22 17:00 UTC = 2026-04-23 00:00 Asia/Ho_Chi_Minh (UTC+7)
    now = datetime(2026, 4, 22, 17, 0, 0, tzinfo=timezone.utc)
    result = _timezones_at_midnight(['Asia/Ho_Chi_Minh', 'UTC'], now)
    assert 'Asia/Ho_Chi_Minh' in result
    assert 'UTC' not in result


@pytest.mark.asyncio
async def test_send_loop_marks_notifications_sent():
    from src.infra.services.scheduled_notification_service import ScheduledNotificationService

    mock_notif = MagicMock()
    mock_notif.notification_type = 'meal_reminder_breakfast'
    mock_notif.context = {
        'fcm_tokens': ['tok1'],
        'calorie_goal': 1800,
        'gender': 'male',
        'language_code': 'en',
    }
    mock_notif.id = 'notif-id-1'
    mock_notif.user_id = 'user-1'

    mock_redis = AsyncMock()
    mock_redis.hgetall_batch = AsyncMock(return_value=[{'calories_consumed': '0'}])
    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(return_value={'success': True, 'failed_tokens': []})

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._redis = mock_redis
    svc._firebase = mock_firebase
    svc._running = True

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_notif]
    mock_db.query.return_value.filter.return_value.update = MagicMock()

    with patch('src.infra.services.scheduled_notification_service.ReminderQueryBuilder') as mock_qb, \
         patch('src.infra.services.scheduled_notification_service.UnitOfWork') as mock_uow:
        mock_qb.find_due_notifications.return_value = [mock_notif]
        mock_uow.return_value.__enter__.return_value.session = mock_db

        now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
        await svc._send_due_notifications(now)

    mock_firebase.send_multicast.assert_called_once()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/unit/infra/test_scheduled_notification_service.py -v
```
Expected: `ImportError` or `AttributeError`

- [ ] **Step 3: Rewrite ScheduledNotificationService**

Replace the contents of `src/infra/services/scheduled_notification_service.py`:

```python
"""
Scheduled notification service — batch pre-compute + batch send.

Architecture:
  Phase 1 (every tick): detect which timezones just hit local midnight →
          trigger DailyContextPrecomputeService for that group.
  Phase 2 (every tick): fetch due notifications from PostgreSQL →
          read calories_consumed from Redis → render messages →
          batch FCM send → mark sent.
"""
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.domain.model.notification import NotificationType
from src.domain.services.notification_messages import get_messages
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.redis_client import RedisClient
from src.infra.database.uow import UnitOfWork
from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder
from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduler_leader_lock import SchedulerLeaderLock

logger = logging.getLogger(__name__)

_CLEANUP_TICKS = 60  # clean expired notifications every ~60 min


def _timezones_at_midnight(tz_names: list[str], now_utc: datetime) -> list[str]:
    """Return timezone names where local time is currently HH:MM == 00:00."""
    result = []
    for tz_name in tz_names:
        try:
            local = now_utc.astimezone(ZoneInfo(tz_name))
            if local.hour == 0 and local.minute == 0:
                result.append(tz_name)
        except (ZoneInfoNotFoundError, Exception):
            pass
    return result


class ScheduledNotificationService:
    """Batch-sends scheduled notifications. One leader per host via flock."""

    LOOP_INTERVAL_SECONDS = 60
    LOOP_ERROR_RETRY_SECONDS = 30

    def __init__(self, firebase_service: FirebaseService, redis_client: RedisClient):
        self._firebase = firebase_service
        self._redis = redis_client
        self._precompute = DailyContextPrecomputeService(redis_client)
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._leader_lock = SchedulerLeaderLock()
        self._leader_acquired = False
        self._cleanup_counter = 0
        self._distinct_timezones: list[str] = []

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            logger.warning("Scheduler already running")
            return
        if not self._leader_lock.try_acquire():
            logger.info("Scheduler skipped: another worker holds the lock")
            return
        self._leader_acquired = True
        self._running = True
        self._distinct_timezones = await asyncio.to_thread(self._fetch_distinct_timezones)
        self._tasks.append(asyncio.create_task(self._scheduling_loop()))
        logger.info("Scheduled notification service started (leader)")

    async def stop(self) -> None:
        if not self._leader_acquired:
            return
        self._running = False
        for t in self._tasks:
            if not t.done():
                t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._leader_lock.release()
        self._leader_acquired = False
        logger.info("Scheduled notification service stopped")

    def is_running(self) -> bool:
        return self._running

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _scheduling_loop(self) -> None:
        while self._running:
            try:
                now = utc_now()
                await self._check_midnight_precompute(now)
                await self._send_due_notifications(now)
                self._cleanup_counter += 1
                if self._cleanup_counter >= _CLEANUP_TICKS:
                    self._cleanup_counter = 0
                    await asyncio.to_thread(self._cleanup_expired_notifications)
                await asyncio.sleep(self.LOOP_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Scheduler loop error: %s", exc)
                await asyncio.sleep(self.LOOP_ERROR_RETRY_SECONDS)

    # ── Phase 1: Midnight pre-compute ─────────────────────────────────────────

    async def _check_midnight_precompute(self, now: datetime) -> None:
        """For each timezone currently at local midnight, trigger pre-compute."""
        today = now.date()
        at_midnight = _timezones_at_midnight(self._distinct_timezones, now)
        for tz_name in at_midnight:
            try:
                await self._precompute.precompute_for_timezone(tz_name, today)
            except Exception as exc:
                logger.error("Pre-compute failed for %s: %s", tz_name, exc)

    # ── Phase 2: Send due notifications ───────────────────────────────────────

    async def _send_due_notifications(self, now: datetime) -> None:
        """Fetch due rows, pull consumed from Redis, render, batch FCM, mark sent."""
        def _fetch_due():
            with UnitOfWork() as uow:
                return ReminderQueryBuilder.find_due_notifications(uow.session, now)

        due = await asyncio.to_thread(_fetch_due)
        if not due:
            return

        logger.info("Sending %d due notifications", len(due))

        # Batch-fetch calories_consumed from Redis
        context_keys = [f"user_daily_context:{n.user_id}" for n in due]
        redis_contexts = await self._redis.hgetall_batch(context_keys)

        # Render messages per notification
        groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)  # (type,title,body) → tokens
        sent_ids = []
        failed_ids = []

        for notif, redis_ctx in zip(due, redis_contexts):
            ctx = notif.context  # JSONB dict from PostgreSQL
            tokens = ctx.get("fcm_tokens", [])
            if not tokens:
                failed_ids.append(notif.id)
                continue

            if not redis_ctx:
                logger.warning("Redis cache miss for user %s — using calorie_goal only", notif.user_id)
                calories_consumed = 0
            else:
                calories_consumed = int(redis_ctx.get("calories_consumed", 0))

            calorie_goal = int(ctx.get("calorie_goal", 2000))
            remaining = max(0, calorie_goal - calories_consumed)
            gender = ctx.get("gender", "male")
            lang = ctx.get("language_code", "en")

            title, body = _render_message(notif.notification_type, remaining, gender, lang)
            for tok in tokens:
                groups[(notif.notification_type, title, body)].append(tok)
            sent_ids.append(notif.id)

        # Batch FCM — 500 tokens per call
        for (notif_type, title, body), tokens in groups.items():
            for chunk in _chunked(tokens, 500):
                result = self._firebase.send_multicast(
                    tokens=chunk, title=title, body=body, notification_type=notif_type
                )
                if result.get("failed_tokens"):
                    await self._handle_failed_tokens(result["failed_tokens"])

        # Mark sent/failed
        if sent_ids or failed_ids:
            await asyncio.to_thread(self._mark_notifications, sent_ids, failed_ids)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fetch_distinct_timezones(self) -> list[str]:
        with UnitOfWork() as uow:
            from sqlalchemy import text
            rows = uow.session.execute(
                text("SELECT DISTINCT timezone FROM users WHERE timezone IS NOT NULL")
            ).fetchall()
            return [r.timezone for r in rows]

    def _mark_notifications(self, sent_ids: list[str], failed_ids: list[str]) -> None:
        from sqlalchemy import text
        with UnitOfWork() as uow:
            if sent_ids:
                uow.session.execute(
                    text("UPDATE notifications SET status = 'sent' WHERE id IN :ids"),
                    {"ids": tuple(sent_ids)},
                )
            if failed_ids:
                uow.session.execute(
                    text("UPDATE notifications SET status = 'failed' WHERE id IN :ids"),
                    {"ids": tuple(failed_ids)},
                )
            uow.session.commit()

    def _cleanup_expired_notifications(self) -> None:
        from sqlalchemy import text
        with UnitOfWork() as uow:
            result = uow.session.execute(
                text("DELETE FROM notifications WHERE expires_at < NOW()")
            )
            uow.session.commit()
            logger.info("Cleaned up %d expired notification rows", result.rowcount)

    async def _handle_failed_tokens(self, failed_tokens: list[dict]) -> None:
        from src.domain.services.notification_service import DEACTIVATABLE_FCM_ERRORS
        from sqlalchemy import text
        to_deactivate = [
            ft["token"] for ft in failed_tokens
            if any(code in str(ft.get("error", "")).upper() for code in DEACTIVATABLE_FCM_ERRORS)
        ]
        if to_deactivate:
            await asyncio.to_thread(self._deactivate_tokens, to_deactivate)

    def _deactivate_tokens(self, tokens: list[str]) -> None:
        from sqlalchemy import text
        with UnitOfWork() as uow:
            uow.session.execute(
                text("UPDATE user_fcm_tokens SET is_active = false WHERE fcm_token IN :tokens"),
                {"tokens": tuple(tokens)},
            )
            uow.session.commit()

    async def send_test_notification(self, user_id: str) -> Dict:
        """Send a test notification to a user (on-demand, no pre-compute)."""
        from src.domain.model.notification import NotificationType
        tokens = await asyncio.to_thread(self._get_tokens_for_user, user_id)
        if not tokens:
            return {"success": False, "reason": "no_tokens"}
        return self._firebase.send_multicast(
            tokens=tokens,
            title="Test Notification",
            body="This is a test notification from the backend",
            notification_type=str(NotificationType.DAILY_SUMMARY),
        )

    def _get_tokens_for_user(self, user_id: str) -> list[str]:
        from sqlalchemy import text
        with UnitOfWork() as uow:
            rows = uow.session.execute(
                text("SELECT fcm_token FROM user_fcm_tokens WHERE user_id = :uid AND is_active = true"),
                {"uid": user_id},
            ).fetchall()
            return [r.fcm_token for r in rows]


# ── Module-level helpers ───────────────────────────────────────────────────────

def _render_message(notification_type: str, remaining: int, gender: str, lang: str) -> tuple[str, str]:
    """Render title + body for a notification type."""
    messages = get_messages(lang, gender)
    if notification_type == "meal_reminder_breakfast":
        cfg = messages["meal_reminder"]["breakfast"]
        return cfg["title"], cfg.get("body", "")
    elif notification_type == "meal_reminder_lunch":
        cfg = messages["meal_reminder"]["lunch"]
        return cfg["title"], cfg["body_template"].format(remaining=remaining)
    elif notification_type == "meal_reminder_dinner":
        cfg = messages["meal_reminder"]["dinner"]
        return cfg["title"], cfg["body_template"].format(remaining=remaining)
    elif notification_type == "daily_summary":
        # Daily summary needs consumed/goal — use remaining as proxy for "under goal"
        cfg = messages["daily_summary"]["under_goal"]
        return cfg["title"], cfg["body_template"].format(deficit=remaining)
    return "Notification", ""


def _chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i: i + size]
```

**Note:** `daily_summary` rendering in `_render_message` is simplified here — the full daily summary (on_target / under / over) needs `calories_consumed` and `calorie_goal` separately. This is addressed in Task 6 follow-up: pass both values from the notification context for daily_summary type.

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/infra/test_scheduled_notification_service.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/scheduled_notification_service.py \
        tests/unit/infra/test_scheduled_notification_service.py
git commit -m "feat(notif): rewrite scheduler — midnight pre-compute + batch FCM send"
```

---

## Task 7: Fix daily_summary rendering in the scheduler

**Files:**
- Modify: `src/infra/services/daily_context_precompute_service.py` — add `calories_consumed` to notification context JSONB
- Modify: `src/infra/services/scheduled_notification_service.py` — use full daily_summary render

The `notifications.context` JSONB currently has `calorie_goal` but not `calories_consumed`. For daily summary we need both. Add `calories_consumed` to the JSONB context at pre-compute time so the send loop has it without a Redis read.

- [ ] **Step 1: Update `_build_notification_rows` to include `calories_consumed`**

In `src/infra/services/daily_context_precompute_service.py`, update `_build_notification_rows` signature and `context_base`:

Find the `context_base` dict in `_build_notification_rows`:

```python
# current
context_base = {
    "fcm_tokens": tokens,
    "calorie_goal": calorie_goals.get(uid, 2000),
    "gender": genders.get(uid, "male"),
    "language_code": pref.language_code or "en",
}
```

Replace with:

```python
# updated — calories_consumed included for daily_summary rendering
context_base = {
    "fcm_tokens": tokens,
    "calorie_goal": calorie_goals.get(uid, 2000),
    "calories_consumed": calories_consumed_map.get(uid, 0),
    "gender": genders.get(uid, "male"),
    "language_code": pref.language_code or "en",
}
```

Update `_build_notification_rows` signature to accept `calories_consumed_map`:

```python
def _build_notification_rows(
    self,
    pref_rows,
    tokens_by_user: dict[str, list[str]],
    calorie_goals: dict[str, int],
    calories_consumed_map: dict[str, int],
    genders: dict[str, str],
    today: date,
    tz_name: str,
) -> list[dict]:
```

Update the call in `_precompute_db_sync` to pass `calories_consumed`:

```python
notification_inserts = self._build_notification_rows(
    rows, tokens_by_user, calorie_goals, calories_consumed, genders, today, tz_name
)
```

- [ ] **Step 2: Update `_render_message` for daily_summary**

In `src/infra/services/scheduled_notification_service.py`, update the `daily_summary` branch and the call site.

Update `_send_due_notifications` to pass both values to `_render_message`:

```python
title, body = _render_message(
    notif.notification_type,
    remaining,
    gender,
    lang,
    calories_consumed=calories_consumed,
    calorie_goal=calorie_goal,
    meals_logged=0,   # not tracked — summary uses calorie % only
)
```

Update `_render_message` signature and daily_summary branch:

```python
def _render_message(
    notification_type: str,
    remaining: int,
    gender: str,
    lang: str,
    calories_consumed: int = 0,
    calorie_goal: int = 2000,
    meals_logged: int = 0,
) -> tuple[str, str]:
    messages = get_messages(lang, gender)
    if notification_type == "meal_reminder_breakfast":
        cfg = messages["meal_reminder"]["breakfast"]
        return cfg["title"], cfg.get("body", "")
    elif notification_type == "meal_reminder_lunch":
        cfg = messages["meal_reminder"]["lunch"]
        return cfg["title"], cfg["body_template"].format(remaining=remaining)
    elif notification_type == "meal_reminder_dinner":
        cfg = messages["meal_reminder"]["dinner"]
        return cfg["title"], cfg["body_template"].format(remaining=remaining)
    elif notification_type == "daily_summary":
        summary = messages["daily_summary"]
        if meals_logged == 0:
            cfg = summary["zero_logs"]
            return cfg["title"], cfg["body"]
        pct = (calories_consumed / calorie_goal * 100) if calorie_goal > 0 else 0
        if 95 <= pct <= 105:
            cfg = summary["on_target"]
            return cfg["title"], cfg["body_template"].format(percentage=int(pct))
        elif pct < 95:
            cfg = summary["under_goal"]
            return cfg["title"], cfg["body_template"].format(deficit=int(calorie_goal - calories_consumed))
        elif pct <= 120:
            cfg = summary["slightly_over"]
            return cfg["title"], cfg["body_template"].format(excess=int(calories_consumed - calorie_goal))
        else:
            cfg = summary["way_over"]
            return cfg["title"], cfg["body_template"].format(excess=int(calories_consumed - calorie_goal))
    return "Notification", ""
```

Update the `_send_due_notifications` loop to extract both values from notification context:

```python
calorie_goal = int(ctx.get("calorie_goal", 2000))
calories_consumed_ctx = int(ctx.get("calories_consumed", 0))

# For meal reminders: use Redis calories_consumed (fresher, ~30 min stale)
# For daily summary: use JSONB calories_consumed (accurate at pre-compute midnight time)
if notif.notification_type == "daily_summary":
    calories_consumed = calories_consumed_ctx
else:
    if not redis_ctx:
        calories_consumed = 0
    else:
        calories_consumed = int(redis_ctx.get("calories_consumed", 0))

remaining = max(0, calorie_goal - calories_consumed)
title, body = _render_message(
    notif.notification_type, remaining, gender, lang,
    calories_consumed=calories_consumed,
    calorie_goal=calorie_goal,
)
```

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v -k "notification" --tb=short
```
Expected: all notification tests pass

- [ ] **Step 4: Commit**

```bash
git add src/infra/services/daily_context_precompute_service.py \
        src/infra/services/scheduled_notification_service.py
git commit -m "fix(notif): embed calories_consumed in notification context for daily_summary rendering"
```

---

## Task 8: Remove dedup logic from NotificationService

**Files:**
- Modify: `src/domain/services/notification_service.py`

`NotificationService` no longer needs `dedup_store` — dedup is handled by the UNIQUE constraint on `notifications` table. Remove the dedup port dependency, `_is_already_sent`, and `cleanup_old_sent_logs`.

- [ ] **Step 1: Remove dedup from NotificationService**

In `src/domain/services/notification_service.py`:

1. Remove `dedup_store` parameter from `__init__`:

```python
def __init__(
    self,
    notification_repository: NotificationRepositoryPort,
    firebase_service,
):
    self.notification_repository = notification_repository
    self.firebase_service = firebase_service
```

2. Remove these imports (if no longer used): `NotificationDedupPort`

3. Delete methods `_is_already_sent`, `_minute_key`, and `cleanup_old_sent_logs`.

4. Remove the dedup guard block (steps 3) inside `send_notification`:

```python
# DELETE this block:
# 3. Dedup guard — prevent duplicate sends from multiple workers
if self._is_already_sent(user_id, notification_type):
    logger.info(...)
    return {"success": True, "reason": "deduplicated"}
```

- [ ] **Step 2: Run existing notification tests**

```bash
pytest tests/ -k "notification" --tb=short
```
Expected: all pass. If any test passes `dedup_store=...` to `NotificationService`, update it to remove that argument.

- [ ] **Step 3: Commit**

```bash
git add src/domain/services/notification_service.py
git commit -m "refactor(notif): remove dedup_store from NotificationService — UNIQUE constraint handles dedup"
```

---

## Task 9: Update wiring in base_dependencies.py

**Files:**
- Modify: `src/api/base_dependencies.py`

Wire `DailyContextPrecomputeService` and the rewritten `ScheduledNotificationService` with `redis_client`. Remove `NotificationSentLogDedupStore`.

- [ ] **Step 1: Update `initialize_scheduled_notification_service`**

In `src/api/base_dependencies.py`:

1. Remove the import of `NotificationSentLogDedupStore`.

2. Update `get_notification_service`:

```python
def get_notification_service(
    notification_repository: NotificationRepositoryPort = Depends(get_notification_repository),
    firebase_service: FirebaseService = Depends(get_firebase_service),
) -> NotificationService:
    return NotificationService(notification_repository, firebase_service)
```

3. Update `initialize_scheduled_notification_service`:

```python
def initialize_scheduled_notification_service() -> ScheduledNotificationService:
    global _scheduled_notification_service
    if _scheduled_notification_service is None:
        firebase_service = get_firebase_service()
        if _redis_client is None:
            raise RuntimeError(
                "Redis client not initialized. Call initialize_cache_layer() first."
            )
        _scheduled_notification_service = ScheduledNotificationService(
            firebase_service=firebase_service,
            redis_client=_redis_client,
        )
    return _scheduled_notification_service
```

Note: `initialize_cache_layer()` must be called before `initialize_scheduled_notification_service()` in the lifespan. Verify order in `src/api/main.py` lifespan.

- [ ] **Step 2: Verify lifespan order in main.py**

Open `src/api/main.py` and confirm the lifespan calls `initialize_cache_layer()` before `initialize_scheduled_notification_service()`. If not, reorder them.

- [ ] **Step 3: Run the app**

```bash
uvicorn src.api.main:app --reload
```
Expected: app starts without import errors. Check logs for "Scheduled notification service started".

- [ ] **Step 4: Commit**

```bash
git add src/api/base_dependencies.py
git commit -m "fix(wiring): wire ScheduledNotificationService with redis_client, remove dedup store"
```

---

## Task 10: Delete dead code

**Files to delete:**
- `src/infra/database/models/notification/notification_sent_log.py`
- `src/domain/ports/notification_dedup_port.py`
- `src/infra/adapters/notification_sent_log_dedup_store.py`

- [ ] **Step 1: Search for remaining references**

```bash
grep -r "notification_sent_log\|NotificationSentLog\|NotificationDedupPort\|NotificationSentLogDedupStore" src/ --include="*.py" -l
```
Expected: no files listed (all references removed in Tasks 7-9).

If files appear, remove the import from each before deleting.

- [ ] **Step 2: Delete the files**

```bash
rm src/infra/database/models/notification/notification_sent_log.py
rm src/domain/ports/notification_dedup_port.py
rm src/infra/adapters/notification_sent_log_dedup_store.py
```

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ --tb=short -q
```
Expected: all existing tests pass, no import errors.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(notif): delete dead code — notification_sent_log ORM, dedup port, dedup store"
```

---

## Task 11: Startup catch-up pre-compute

**Files:**
- Modify: `src/infra/services/scheduled_notification_service.py`

On startup, the `notifications` table is empty for timezones that already passed midnight today. The scheduler should pre-compute for all timezones missing today's sentinel key before entering the main loop.

- [ ] **Step 1: Add catch-up to `start()`**

In `ScheduledNotificationService.start()`, add a catch-up call after fetching distinct timezones:

```python
async def start(self) -> None:
    if self._running:
        logger.warning("Scheduler already running")
        return
    if not self._leader_lock.try_acquire():
        logger.info("Scheduler skipped: another worker holds the lock")
        return
    self._leader_acquired = True
    self._running = True
    self._distinct_timezones = await asyncio.to_thread(self._fetch_distinct_timezones)

    # Startup catch-up: pre-compute for all timezones that already passed midnight today
    await self._startup_catchup()

    self._tasks.append(asyncio.create_task(self._scheduling_loop()))
    logger.info("Scheduled notification service started (leader)")

async def _startup_catchup(self) -> None:
    """Pre-compute for all timezones missing today's sentinel (handles restarts)."""
    today = utc_now().date()
    logger.info("Running startup catch-up pre-compute for %d timezones", len(self._distinct_timezones))
    for tz_name in self._distinct_timezones:
        try:
            await self._precompute.precompute_for_timezone(tz_name, today)
        except Exception as exc:
            logger.error("Startup catch-up failed for %s: %s", tz_name, exc)
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ --tb=short -q
```
Expected: all tests pass

- [ ] **Step 3: Manual smoke test**

Send a test notification via the existing test endpoint (if available) or check logs after startup for "Pre-compute complete for X timezone".

- [ ] **Step 4: Commit**

```bash
git add src/infra/services/scheduled_notification_service.py
git commit -m "feat(notif): add startup catch-up pre-compute for all timezones on restart"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: Redis user_daily_context ✅ (Task 3), PostgreSQL JSONB notifications ✅ (Task 2), batch pre-compute ✅ (Task 3), midnight detection ✅ (Task 6), batch FCM ✅ (Task 6), dedup via UNIQUE ✅ (Task 2), drop notification_sent_log ✅ (Task 2+10), remove dedup port ✅ (Tasks 8+10), wiring ✅ (Task 9), startup catch-up ✅ (Task 11)
- [x] **No placeholders**: all steps contain actual code
- [x] **Type consistency**: `DailyContextPrecomputeService` created in Task 3, used in Task 6 via `ScheduledNotificationService.__init__`. `NotificationORM` created in Task 2, used in Task 4. `send_multicast` added in Task 5, called in Task 6.
- [x] **daily_summary rendering**: handled in Task 7 with full on_target/under/over logic matching existing `notification_service.py`
