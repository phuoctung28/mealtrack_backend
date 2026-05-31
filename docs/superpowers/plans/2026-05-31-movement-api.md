# Movement API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build backend-owned movement catalog/MET values, movement log/daily/delete APIs, and movement calorie balance integration.

**Architecture:** Add a dedicated Movement bounded context following the existing FastAPI + CQRS + AsyncUnitOfWork patterns. Preset catalog data lives in a dependency-free domain service; user movement entries live in a new `movement_entries` table and repository. Nutrition summaries subtract included movement kcal from net consumed calories without changing macro totals.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2 async ORM, Alembic, PyMediator event bus, pytest.

---

## File Map

Create:

- `src/domain/model/movement/__init__.py`: movement domain exports.
- `src/domain/model/movement/movement_enums.py`: `MovementIntensity`, `MovementSource`.
- `src/domain/model/movement/movement_entry.py`: dependency-free movement entity.
- `src/domain/services/movement_catalog_service.py`: static preset catalog and lookup helpers.
- `src/app/commands/movement/__init__.py`: movement command exports.
- `src/app/commands/movement/log_movement_command.py`: log command DTO.
- `src/app/commands/movement/delete_movement_entry_command.py`: delete command DTO.
- `src/app/queries/movement/__init__.py`: movement query exports.
- `src/app/queries/movement/get_movement_catalog_query.py`: catalog query DTO.
- `src/app/queries/movement/get_daily_movement_query.py`: daily query DTO.
- `src/app/handlers/command_handlers/log_movement_command_handler.py`: validation, timezone resolution, persistence, cache invalidation.
- `src/app/handlers/command_handlers/delete_movement_entry_command_handler.py`: owner-scoped deletion and cache invalidation.
- `src/app/handlers/query_handlers/get_movement_catalog_query_handler.py`: catalog response.
- `src/app/handlers/query_handlers/get_daily_movement_query_handler.py`: daily summary response.
- `src/api/schemas/request/movement_requests.py`: Pydantic request schemas.
- `src/api/routes/v1/movement.py`: `/v1/movement` router.
- `src/infra/database/models/movement_entry.py`: SQLAlchemy ORM model.
- `src/infra/mappers/movement_entry_mapper.py`: ORM/domain mapping.
- `src/infra/repositories/movement_repository_async.py`: async repository.
- `migrations/versions/060_add_movement_entries_table.py`: database migration.
- `tests/unit/domain/services/test_movement_catalog_service.py`: catalog tests.
- `tests/unit/handlers/command_handlers/test_movement_command_handlers.py`: log/delete command handler tests.
- `tests/unit/handlers/query_handlers/test_movement_query_handlers.py`: catalog/daily query tests.
- `tests/unit/api/routes/test_movement_routes.py`: API route tests.
- `tests/unit/handlers/query_handlers/test_movement_balance_integration.py`: nutrition adjustment tests.

Modify:

- `src/infra/database/uow_async.py`: add `movement_entries` repository.
- `src/infra/database/models/__init__.py`: import/export `MovementEntryORM`.
- `src/app/handlers/command_handlers/__init__.py`: import/export movement command handlers.
- `src/app/handlers/query_handlers/__init__.py`: import/export movement query handlers.
- `src/api/dependencies/event_bus.py`: register movement commands/queries.
- `src/api/main.py`: include movement router.
- `src/app/handlers/query_handlers/get_daily_macros_query_handler.py`: subtract included movement kcal.
- `src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py`: subtract included movement kcal per date.

## Task 1: Backend Movement Catalog

**Files:**
- Create: `src/domain/model/movement/movement_enums.py`
- Create: `src/domain/services/movement_catalog_service.py`
- Create: `src/app/queries/movement/get_movement_catalog_query.py`
- Create: `src/app/handlers/query_handlers/get_movement_catalog_query_handler.py`
- Test: `tests/unit/domain/services/test_movement_catalog_service.py`
- Test: `tests/unit/handlers/query_handlers/test_movement_query_handlers.py`

- [ ] **Step 1: Write failing catalog service tests**

Add `tests/unit/domain/services/test_movement_catalog_service.py`:

```python
from src.domain.services.movement_catalog_service import (
    get_all_activities,
    get_activity,
    get_met,
)


def test_catalog_contains_badminton_with_localized_names_and_met_values():
    activities = get_all_activities()

    badminton = next(item for item in activities if item["id"] == "badminton")

    assert badminton["name"]["en"] == "Badminton"
    assert badminton["name"]["vi"] == "Cầu lông"
    assert badminton["met"]["moderate"] == 7.0
    assert badminton["apple_health_type"] == "badminton"


def test_lookup_returns_none_for_unknown_activity():
    assert get_activity("unknown") is None


def test_get_met_returns_intensity_value_or_none():
    assert get_met("walking", "moderate") == 3.8
    assert get_met("badminton", "very_hard") is None
```

- [ ] **Step 2: Run catalog tests to verify RED**

Run:

```bash
pytest tests/unit/domain/services/test_movement_catalog_service.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `movement_catalog_service`.

- [ ] **Step 3: Implement movement enums and catalog service**

Create `src/domain/model/movement/movement_enums.py`:

```python
"""Enums for movement domain constrained values."""

from enum import Enum


class MovementIntensity(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HARD = "hard"


class MovementSource(str, Enum):
    MANUAL = "manual"
    APPLE_HEALTH = "apple_health"
```

Create `src/domain/services/movement_catalog_service.py`:

```python
"""Backend-owned movement activity catalog and MET values."""

from copy import deepcopy
from typing import Any

_ACTIVITIES: list[dict[str, Any]] = [
    {
        "id": "walking",
        "name": {"en": "Walking", "vi": "Đi bộ"},
        "default_met": 3.8,
        "met": {"light": 3.0, "moderate": 3.8, "hard": 4.8},
        "apple_health_type": "walking",
        "is_custom": False,
    },
    {
        "id": "running",
        "name": {"en": "Running", "vi": "Chạy bộ"},
        "default_met": 8.5,
        "met": {"light": 6.5, "moderate": 8.5, "hard": 10.5},
        "apple_health_type": "running",
        "is_custom": False,
    },
    {
        "id": "cycling",
        "name": {"en": "Cycling", "vi": "Đạp xe"},
        "default_met": 7.0,
        "met": {"light": 4.0, "moderate": 7.0, "hard": 9.0},
        "apple_health_type": "cycling",
        "is_custom": False,
    },
    {
        "id": "gym_strength",
        "name": {"en": "Gym / Strength", "vi": "Tập gym"},
        "default_met": 3.5,
        "met": {"light": 3.5, "moderate": 5.0, "hard": 6.0},
        "apple_health_type": "traditionalStrengthTraining",
        "is_custom": False,
    },
    {
        "id": "cardio_hiit",
        "name": {"en": "Cardio / HIIT", "vi": "Cardio / HIIT"},
        "default_met": 7.3,
        "met": {"light": 4.8, "moderate": 7.3, "hard": 7.5},
        "apple_health_type": "highIntensityIntervalTraining",
        "is_custom": False,
    },
    {
        "id": "yoga_stretching",
        "name": {"en": "Yoga / Stretching", "vi": "Yoga / Giãn cơ"},
        "default_met": 2.3,
        "met": {"light": 2.3, "moderate": 4.0, "hard": 8.0},
        "apple_health_type": "yoga",
        "is_custom": False,
    },
    {
        "id": "swimming",
        "name": {"en": "Swimming", "vi": "Bơi lội"},
        "default_met": 6.0,
        "met": {"light": 5.8, "moderate": 6.0, "hard": 8.0},
        "apple_health_type": "swimming",
        "is_custom": False,
    },
    {
        "id": "badminton",
        "name": {"en": "Badminton", "vi": "Cầu lông"},
        "default_met": 5.5,
        "met": {"light": 5.5, "moderate": 7.0, "hard": 9.0},
        "apple_health_type": "badminton",
        "is_custom": False,
    },
    {
        "id": "football",
        "name": {"en": "Football", "vi": "Bóng đá"},
        "default_met": 7.0,
        "met": {"light": 3.5, "moderate": 7.0, "hard": 9.5},
        "apple_health_type": "soccer",
        "is_custom": False,
    },
    {
        "id": "volleyball",
        "name": {"en": "Volleyball", "vi": "Bóng chuyền"},
        "default_met": 4.0,
        "met": {"light": 3.0, "moderate": 4.0, "hard": 6.0},
        "apple_health_type": "volleyball",
        "is_custom": False,
    },
]

_BY_ID = {item["id"]: item for item in _ACTIVITIES}


def get_all_activities() -> list[dict[str, Any]]:
    return deepcopy(_ACTIVITIES)


def get_activity(activity_id: str | None) -> dict[str, Any] | None:
    if not activity_id:
        return None
    item = _BY_ID.get(activity_id)
    return deepcopy(item) if item else None


def get_met(activity_id: str | None, intensity: str) -> float | None:
    item = _BY_ID.get(activity_id or "")
    if not item:
        return None
    value = item["met"].get(intensity)
    return float(value) if value is not None else None
```

- [ ] **Step 4: Run catalog tests to verify GREEN**

Run:

```bash
pytest tests/unit/domain/services/test_movement_catalog_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Add query handler test**

Add to `tests/unit/handlers/query_handlers/test_movement_query_handlers.py`:

```python
import pytest

from src.app.handlers.query_handlers.get_movement_catalog_query_handler import (
    GetMovementCatalogQueryHandler,
)
from src.app.queries.movement import GetMovementCatalogQuery


@pytest.mark.asyncio
async def test_get_movement_catalog_query_returns_activities():
    handler = GetMovementCatalogQueryHandler()

    result = await handler.handle(GetMovementCatalogQuery())

    assert "activities" in result
    assert any(item["id"] == "badminton" for item in result["activities"])
```

- [ ] **Step 6: Run query handler test to verify RED**

Run:

```bash
pytest tests/unit/handlers/query_handlers/test_movement_query_handlers.py::test_get_movement_catalog_query_returns_activities -v
```

Expected: FAIL with missing query or handler module.

- [ ] **Step 7: Implement catalog query files**

Create `src/app/queries/movement/get_movement_catalog_query.py`:

```python
"""Query for backend-owned movement catalog."""

from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMovementCatalogQuery(Query):
    pass
```

Create `src/app/queries/movement/__init__.py`:

```python
"""Movement queries."""

from .get_movement_catalog_query import GetMovementCatalogQuery

__all__ = ["GetMovementCatalogQuery"]
```

Create `src/app/handlers/query_handlers/get_movement_catalog_query_handler.py`:

```python
"""Handler for movement catalog query."""

from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.queries.movement import GetMovementCatalogQuery
from src.domain.services.movement_catalog_service import get_all_activities


@handles(GetMovementCatalogQuery)
class GetMovementCatalogQueryHandler(
    EventHandler[GetMovementCatalogQuery, dict[str, list[dict[str, Any]]]]
):
    async def handle(self, query: GetMovementCatalogQuery) -> dict[str, list[dict[str, Any]]]:
        return {"activities": get_all_activities()}
```

- [ ] **Step 8: Run catalog query tests to verify GREEN**

Run:

```bash
pytest tests/unit/domain/services/test_movement_catalog_service.py tests/unit/handlers/query_handlers/test_movement_query_handlers.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit catalog work**

```bash
git add src/domain/model/movement/movement_enums.py src/domain/services/movement_catalog_service.py src/app/queries/movement src/app/handlers/query_handlers/get_movement_catalog_query_handler.py tests/unit/domain/services/test_movement_catalog_service.py tests/unit/handlers/query_handlers/test_movement_query_handlers.py
git commit -m "feat: add movement catalog"
```

## Task 2: Movement Persistence

**Files:**
- Create: `src/domain/model/movement/movement_entry.py`
- Create: `src/domain/model/movement/__init__.py`
- Create: `src/infra/database/models/movement_entry.py`
- Create: `src/infra/mappers/movement_entry_mapper.py`
- Create: `src/infra/repositories/movement_repository_async.py`
- Create: `migrations/versions/060_add_movement_entries_table.py`
- Modify: `src/infra/database/models/__init__.py`
- Modify: `src/infra/database/uow_async.py`
- Test: `tests/unit/infra/repositories/test_movement_repository_async.py`

- [ ] **Step 1: Write failing repository tests**

Add `tests/unit/infra/repositories/test_movement_repository_async.py` with fake-session-light tests for query construction:

```python
from datetime import datetime, timezone

from src.domain.model.movement import MovementEntry


def test_movement_entry_defaults_to_manual_source_and_include_in_balance():
    entry = MovementEntry(
        user_id="user-1",
        activity_name="Badminton",
        duration_min=60,
        kcal_burned=231.0,
        intensity="moderate",
        logged_at=datetime(2026, 5, 31, 5, 0, tzinfo=timezone.utc),
    )

    assert entry.id.startswith("mvmt_")
    assert entry.source == "manual"
    assert entry.include_in_balance is True
```

- [ ] **Step 2: Run persistence tests to verify RED**

Run:

```bash
pytest tests/unit/infra/repositories/test_movement_repository_async.py -v
```

Expected: FAIL with missing `MovementEntry`.

- [ ] **Step 3: Implement domain model**

Create `src/domain/model/movement/movement_entry.py`:

```python
"""Movement entry domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from src.domain.utils.timezone_utils import utc_now


def _movement_id() -> str:
    return f"mvmt_{uuid.uuid4().hex}"


@dataclass
class MovementEntry:
    user_id: str
    activity_name: str
    duration_min: int
    kcal_burned: float
    intensity: str
    logged_at: datetime
    id: str = field(default_factory=_movement_id)
    activity_id: Optional[str] = None
    source: str = "manual"
    include_in_balance: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_included_in_balance(self) -> bool:
        return self.include_in_balance
```

Create `src/domain/model/movement/__init__.py`:

```python
"""Movement bounded context."""

from .movement_entry import MovementEntry
from .movement_enums import MovementIntensity, MovementSource

__all__ = ["MovementEntry", "MovementIntensity", "MovementSource"]
```

- [ ] **Step 4: Run domain test to verify GREEN**

Run:

```bash
pytest tests/unit/infra/repositories/test_movement_repository_async.py::test_movement_entry_defaults_to_manual_source_and_include_in_balance -v
```

Expected: PASS.

- [ ] **Step 5: Implement ORM, mapper, repository, UoW, and migration**

Create `src/infra/database/models/movement_entry.py`:

```python
"""Movement entry database model."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class MovementEntryORM(Base, BaseMixin):
    __tablename__ = "movement_entries"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(String(64), nullable=True, index=True)
    activity_name = Column(String(100), nullable=False)
    duration_min = Column(Integer, nullable=False)
    kcal_burned = Column(Float, nullable=False)
    intensity = Column(String(16), nullable=False)
    source = Column(String(32), nullable=False, default="manual")
    include_in_balance = Column(Boolean, nullable=False, default=True)
    logged_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_movement_entries_user_logged_at", "user_id", "logged_at"),
    )
```

Create `src/infra/mappers/movement_entry_mapper.py`:

```python
"""MovementEntry ORM <-> domain mapping functions."""

from src.domain.model.movement import MovementEntry
from src.infra.database.models.movement_entry import MovementEntryORM


def movement_entry_orm_to_domain(orm: MovementEntryORM) -> MovementEntry:
    return MovementEntry(
        id=orm.id,
        user_id=orm.user_id,
        activity_id=orm.activity_id,
        activity_name=orm.activity_name,
        duration_min=orm.duration_min,
        kcal_burned=orm.kcal_burned,
        intensity=orm.intensity,
        source=orm.source,
        include_in_balance=orm.include_in_balance,
        logged_at=orm.logged_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def movement_entry_domain_to_orm(domain: MovementEntry) -> MovementEntryORM:
    return MovementEntryORM(
        id=domain.id,
        user_id=domain.user_id,
        activity_id=domain.activity_id,
        activity_name=domain.activity_name,
        duration_min=domain.duration_min,
        kcal_burned=domain.kcal_burned,
        intensity=domain.intensity,
        source=domain.source,
        include_in_balance=domain.include_in_balance,
        logged_at=domain.logged_at,
    )
```

Create `src/infra/repositories/movement_repository_async.py`:

```python
"""Async movement repository."""

from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.movement import MovementEntry
from src.infra.database.models.movement_entry import MovementEntryORM
from src.infra.mappers.movement_entry_mapper import (
    movement_entry_domain_to_orm,
    movement_entry_orm_to_domain,
)


class AsyncMovementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, entry: MovementEntry) -> MovementEntry:
        db = movement_entry_domain_to_orm(entry)
        self.session.add(db)
        await self.session.flush()
        await self.session.refresh(db)
        return movement_entry_orm_to_domain(db)

    async def find_by_user_and_logged_range(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[MovementEntry]:
        result = await self.session.execute(
            select(MovementEntryORM)
            .where(
                MovementEntryORM.user_id == user_id,
                MovementEntryORM.logged_at >= start_utc,
                MovementEntryORM.logged_at < end_utc,
            )
            .order_by(MovementEntryORM.logged_at.desc(), MovementEntryORM.created_at.desc())
        )
        return [movement_entry_orm_to_domain(row) for row in result.scalars().all()]

    async def sum_included_kcal_for_range(
        self,
        user_id: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(MovementEntryORM.kcal_burned), 0.0)).where(
                MovementEntryORM.user_id == user_id,
                MovementEntryORM.include_in_balance.is_(True),
                MovementEntryORM.logged_at >= start_utc,
                MovementEntryORM.logged_at < end_utc,
            )
        )
        return float(result.scalar_one() or 0.0)

    async def delete(self, user_id: str, entry_id: str) -> bool:
        result = await self.session.execute(
            delete(MovementEntryORM).where(
                MovementEntryORM.id == entry_id,
                MovementEntryORM.user_id == user_id,
            )
        )
        return result.rowcount > 0
```

Create `migrations/versions/060_add_movement_entries_table.py`:

```python
"""Add movement_entries table.

Revision ID: 060
Revises: 059
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movement_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", sa.String(64), nullable=True),
        sa.Column("activity_name", sa.String(100), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("kcal_burned", sa.Float(), nullable=False),
        sa.Column("intensity", sa.String(16), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("include_in_balance", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("idx_movement_entries_user_id", "movement_entries", ["user_id"])
    op.create_index("idx_movement_entries_activity_id", "movement_entries", ["activity_id"])
    op.create_index("idx_movement_entries_user_logged_at", "movement_entries", ["user_id", "logged_at"])


def downgrade() -> None:
    op.drop_index("idx_movement_entries_user_logged_at", table_name="movement_entries")
    op.drop_index("idx_movement_entries_activity_id", table_name="movement_entries")
    op.drop_index("idx_movement_entries_user_id", table_name="movement_entries")
    op.drop_table("movement_entries")
```

Modify `src/infra/database/uow_async.py`:

```python
from src.infra.repositories.movement_repository_async import AsyncMovementRepository
```

and inside `_init_repositories`:

```python
self.movement_entries = AsyncMovementRepository(session)
```

Modify `src/infra/database/models/__init__.py` by adding:

```python
from .movement_entry import MovementEntryORM
```

and add `"MovementEntryORM"` to `__all__`.

- [ ] **Step 6: Run focused import tests**

Run:

```bash
pytest tests/unit/infra/repositories/test_movement_repository_async.py -v
python -m compileall src/domain/model/movement src/infra/repositories/movement_repository_async.py src/infra/database/models/movement_entry.py
```

Expected: PASS and compile succeeds.

- [ ] **Step 7: Commit persistence work**

```bash
git add src/domain/model/movement src/infra/database/models/movement_entry.py src/infra/database/models/__init__.py src/infra/mappers/movement_entry_mapper.py src/infra/repositories/movement_repository_async.py src/infra/database/uow_async.py migrations/versions/060_add_movement_entries_table.py tests/unit/infra/repositories/test_movement_repository_async.py
git commit -m "feat: add movement persistence"
```

## Task 3: Movement Log, Daily, Delete Handlers

**Files:**
- Create: `src/app/commands/movement/log_movement_command.py`
- Create: `src/app/commands/movement/delete_movement_entry_command.py`
- Create: `src/app/queries/movement/get_daily_movement_query.py`
- Create: movement command/query handlers listed in File Map
- Modify: movement `__init__.py` exports
- Test: command and query handler tests

- [ ] **Step 1: Write failing handler tests**

Add to `tests/unit/handlers/command_handlers/test_movement_command_handlers.py`:

```python
import pytest

from src.app.commands.movement import LogMovementCommand
from src.app.handlers.command_handlers.log_movement_command_handler import (
    _validate_log_movement,
)
from src.api.exceptions import ValidationException


def test_validate_log_movement_accepts_catalog_activity():
    _validate_log_movement(
        LogMovementCommand(
            user_id="user-1",
            activity_id="badminton",
            activity_name="Badminton",
            duration_min=60,
            kcal_burned=231.0,
            intensity="moderate",
            include_in_balance=True,
        )
    )


def test_validate_log_movement_rejects_unknown_activity_id():
    with pytest.raises(ValidationException) as exc:
        _validate_log_movement(
            LogMovementCommand(
                user_id="user-1",
                activity_id="unknown",
                activity_name="Unknown",
                duration_min=60,
                kcal_burned=231.0,
                intensity="moderate",
                include_in_balance=True,
            )
        )

    assert exc.value.error_code == "INVALID_ACTIVITY"
```

- [ ] **Step 2: Run handler tests to verify RED**

Run:

```bash
pytest tests/unit/handlers/command_handlers/test_movement_command_handlers.py -v
```

Expected: FAIL with missing command/handler.

- [ ] **Step 3: Implement commands, daily query, handlers**

Create `src/app/commands/movement/log_movement_command.py`:

```python
"""Command to log a movement entry."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Command


@dataclass
class LogMovementCommand(Command):
    user_id: str
    activity_name: str
    duration_min: int
    kcal_burned: float
    intensity: str
    include_in_balance: bool
    activity_id: Optional[str] = None
    target_date: Optional[date] = None
    header_timezone: Optional[str] = None
```

Create `src/app/commands/movement/delete_movement_entry_command.py`:

```python
"""Command to delete a movement entry."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class DeleteMovementEntryCommand(Command):
    user_id: str
    entry_id: str
```

Create `src/app/commands/movement/__init__.py`:

```python
"""Movement commands."""

from .delete_movement_entry_command import DeleteMovementEntryCommand
from .log_movement_command import LogMovementCommand

__all__ = ["DeleteMovementEntryCommand", "LogMovementCommand"]
```

Create `src/app/queries/movement/get_daily_movement_query.py`:

```python
"""Query for daily movement summary."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetDailyMovementQuery(Query):
    user_id: str
    target_date: Optional[date] = None
    header_timezone: Optional[str] = None
```

Update `src/app/queries/movement/__init__.py`:

```python
"""Movement queries."""

from .get_daily_movement_query import GetDailyMovementQuery
from .get_movement_catalog_query import GetMovementCatalogQuery

__all__ = ["GetDailyMovementQuery", "GetMovementCatalogQuery"]
```

Create `src/app/handlers/command_handlers/log_movement_command_handler.py`:

```python
"""Command handler for logging movement entries."""

from datetime import timedelta
from typing import Any, Optional

from src.api.exceptions import ValidationException
from src.app.commands.movement import LogMovementCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.movement import MovementEntry
from src.domain.services.movement_catalog_service import get_activity, get_met
from src.domain.utils.timezone_utils import (
    noon_utc_for_date,
    resolve_user_timezone_async,
    user_today,
)
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork


def _movement_response(entry: MovementEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "activity_id": entry.activity_id,
        "activity_name": entry.activity_name,
        "duration_min": entry.duration_min,
        "kcal_burned": entry.kcal_burned,
        "intensity": entry.intensity,
        "source": entry.source,
        "include_in_balance": entry.include_in_balance,
        "logged_at": entry.logged_at.isoformat() if entry.logged_at else None,
    }


def _validate_log_movement(cmd: LogMovementCommand) -> None:
    if not cmd.activity_name or len(cmd.activity_name.strip()) > 100:
        raise ValidationException("activity_name must be 1-100 characters", "INVALID_ACTIVITY")
    if cmd.duration_min < 1 or cmd.duration_min > 600:
        raise ValidationException("duration_min must be between 1 and 600", "INVALID_DURATION")
    if cmd.kcal_burned < 0:
        raise ValidationException("kcal_burned must be non-negative", "INVALID_KCAL")
    if cmd.intensity not in {"light", "moderate", "hard"}:
        raise ValidationException("Invalid intensity", "INVALID_INTENSITY")
    if cmd.activity_id:
        if not get_activity(cmd.activity_id):
            raise ValidationException("Unknown movement activity", "INVALID_ACTIVITY")
        if get_met(cmd.activity_id, cmd.intensity) is None:
            raise ValidationException("Intensity not supported for activity", "INVALID_INTENSITY")


async def _invalidate_movement_caches(
    cache_service: Optional[CachePort],
    user_id: str,
    target_date,
) -> None:
    if not cache_service:
        return
    daily_key, _ = CacheKeys.daily_macros(user_id, target_date)
    await cache_service.invalidate(daily_key)
    activities_pattern = f"user:{user_id}:activities:{target_date.isoformat()}:*"
    await cache_service.invalidate_pattern(activities_pattern)


@handles(LogMovementCommand)
class LogMovementCommandHandler(EventHandler[LogMovementCommand, dict[str, Any]]):
    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, cmd: LogMovementCommand) -> dict[str, Any]:
        _validate_log_movement(cmd)
        async with AsyncUnitOfWork() as uow:
            user_tz = await resolve_user_timezone_async(
                cmd.user_id,
                uow,
                cmd.header_timezone,
            )
            target_date = cmd.target_date or user_today(user_tz)
            if target_date > user_today(user_tz) + timedelta(days=1):
                raise ValidationException("target_date cannot be more than one day in the future", "INVALID_DATE")
            logged_at = noon_utc_for_date(target_date, user_tz)
            entry = MovementEntry(
                user_id=cmd.user_id,
                activity_id=cmd.activity_id,
                activity_name=cmd.activity_name.strip(),
                duration_min=cmd.duration_min,
                kcal_burned=cmd.kcal_burned,
                intensity=cmd.intensity,
                include_in_balance=cmd.include_in_balance,
                logged_at=logged_at,
            )
            saved = await uow.movement_entries.add(entry)
            await uow.commit()
        await _invalidate_movement_caches(self.cache_service, cmd.user_id, target_date)
        return _movement_response(saved)
```

Create `src/app/handlers/command_handlers/delete_movement_entry_command_handler.py`:

```python
"""Command handler for deleting movement entries."""

from typing import Any, Optional

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.movement import DeleteMovementEntryCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork


@handles(DeleteMovementEntryCommand)
class DeleteMovementEntryCommandHandler(
    EventHandler[DeleteMovementEntryCommand, dict[str, Any]]
):
    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, cmd: DeleteMovementEntryCommand) -> dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            deleted = await uow.movement_entries.delete(cmd.user_id, cmd.entry_id)
            if not deleted:
                raise ResourceNotFoundException(
                    "Movement entry not found",
                    "ENTRY_NOT_FOUND",
                )
            await uow.commit()
        return {}
```

Create `src/app/handlers/query_handlers/get_daily_movement_query_handler.py`:

```python
"""Handler for daily movement summary."""

from datetime import datetime, time, timedelta, timezone
from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.log_movement_command_handler import (
    _movement_response,
)
from src.app.queries.movement import GetDailyMovementQuery
from src.domain.utils.timezone_utils import (
    get_zone_info,
    resolve_user_timezone_async,
    user_today,
)
from src.infra.database.uow_async import AsyncUnitOfWork


def _local_day_utc_range(target_date, user_tz_str: str):
    tz = get_zone_info(user_tz_str)
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


@handles(GetDailyMovementQuery)
class GetDailyMovementQueryHandler(
    EventHandler[GetDailyMovementQuery, dict[str, Any]]
):
    async def handle(self, query: GetDailyMovementQuery) -> dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            user_tz = await resolve_user_timezone_async(
                query.user_id,
                uow,
                query.header_timezone,
            )
            target_date = query.target_date or user_today(user_tz)
            start_utc, end_utc = _local_day_utc_range(target_date, user_tz)
            entries = await uow.movement_entries.find_by_user_and_logged_range(
                query.user_id,
                start_utc,
                end_utc,
            )
        return {
            "date": target_date.isoformat(),
            "goal_kcal": 300.0,
            "entries": [_movement_response(entry) for entry in entries],
        }
```

- [ ] **Step 4: Run handler tests**

Run:

```bash
pytest tests/unit/handlers/command_handlers/test_movement_command_handlers.py tests/unit/handlers/query_handlers/test_movement_query_handlers.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit handler work**

```bash
git add src/app/commands/movement src/app/queries/movement src/app/handlers/command_handlers/*movement* src/app/handlers/query_handlers/*movement* tests/unit/handlers/command_handlers/test_movement_command_handlers.py tests/unit/handlers/query_handlers/test_movement_query_handlers.py
git commit -m "feat: add movement handlers"
```

## Task 4: Movement API Routes And Event Bus Registration

**Files:**
- Create: `src/api/schemas/request/movement_requests.py`
- Create: `src/api/routes/v1/movement.py`
- Modify: `src/api/main.py`
- Modify: `src/api/dependencies/event_bus.py`
- Modify: handler package `__init__.py` files
- Test: `tests/unit/api/routes/test_movement_routes.py`

- [ ] **Step 1: Write failing route tests**

Add `tests/unit/api/routes/test_movement_routes.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.v1.movement import router


def test_movement_catalog_route_returns_activities(monkeypatch):
    app = FastAPI()
    app.include_router(router)

    async def fake_user_id():
        return "user-1"

    class FakeBus:
        async def send(self, query):
            return {"activities": [{"id": "badminton", "met": {"moderate": 7.0}}]}

    from src.api.dependencies.auth import get_current_user_id
    from src.api.dependencies.event_bus import get_configured_event_bus

    app.dependency_overrides[get_current_user_id] = fake_user_id
    app.dependency_overrides[get_configured_event_bus] = lambda: FakeBus()

    response = TestClient(app).get("/v1/movement/catalog")

    assert response.status_code == 200
    assert response.json()["activities"][0]["id"] == "badminton"
```

- [ ] **Step 2: Run route tests to verify RED**

Run:

```bash
pytest tests/unit/api/routes/test_movement_routes.py -v
```

Expected: FAIL with missing route module.

- [ ] **Step 3: Implement request schemas and router**

Create `src/api/schemas/request/movement_requests.py`:

```python
"""Movement request schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class LogMovementRequest(BaseModel):
    activity_id: Optional[str] = Field(None, max_length=64)
    activity_name: str = Field(..., min_length=1, max_length=100)
    duration_min: int = Field(..., ge=1, le=600)
    kcal_burned: float = Field(..., ge=0)
    intensity: str
    include_in_balance: bool
    target_date: Optional[str] = None
```

Create `src/api/routes/v1/movement.py`:

```python
"""Movement API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import ValidationException, handle_exception
from src.api.schemas.request.movement_requests import LogMovementRequest
from src.app.commands.movement import DeleteMovementEntryCommand, LogMovementCommand
from src.app.queries.movement import GetDailyMovementQuery, GetMovementCatalogQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/movement", tags=["Movement"])


def _parse_date(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationException("Invalid date format. Use YYYY-MM-DD", "INVALID_DATE") from exc


@router.get("/catalog")
async def get_movement_catalog(
    _: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        return await event_bus.send(GetMovementCatalogQuery())
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.post("/log", status_code=status.HTTP_201_CREATED)
async def log_movement(
    body: LogMovementRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        command = LogMovementCommand(
            user_id=user_id,
            activity_id=body.activity_id,
            activity_name=body.activity_name,
            duration_min=body.duration_min,
            kcal_burned=body.kcal_burned,
            intensity=body.intensity,
            include_in_balance=body.include_in_balance,
            target_date=_parse_date(body.target_date),
            header_timezone=request.headers.get("X-Timezone"),
        )
        return await event_bus.send(command)
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.get("/daily")
async def get_daily_movement(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    date: Optional[str] = Query(None),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        query = GetDailyMovementQuery(
            user_id=user_id,
            target_date=_parse_date(date),
            header_timezone=request.headers.get("X-Timezone"),
        )
        return await event_bus.send(query)
    except Exception as exc:
        raise handle_exception(exc) from exc


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movement_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus),
):
    try:
        await event_bus.send(DeleteMovementEntryCommand(user_id=user_id, entry_id=entry_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise handle_exception(exc) from exc
```

- [ ] **Step 4: Register router and event handlers**

Modify `src/api/main.py`:

```python
from src.api.routes.v1.movement import router as movement_router
app.include_router(movement_router)
```

Modify `src/api/dependencies/event_bus.py` to import and register:

```python
from src.app.commands.movement import DeleteMovementEntryCommand, LogMovementCommand
from src.app.queries.movement import GetDailyMovementQuery, GetMovementCatalogQuery
from src.app.handlers.command_handlers import DeleteMovementEntryCommandHandler, LogMovementCommandHandler
from src.app.handlers.query_handlers import GetDailyMovementQueryHandler, GetMovementCatalogQueryHandler
```

and in the configured bus function:

```python
event_bus.register_handler(LogMovementCommand, LogMovementCommandHandler(cache_service=cache_service))
event_bus.register_handler(DeleteMovementEntryCommand, DeleteMovementEntryCommandHandler(cache_service=cache_service))
event_bus.register_handler(GetMovementCatalogQuery, GetMovementCatalogQueryHandler())
event_bus.register_handler(GetDailyMovementQuery, GetDailyMovementQueryHandler())
```

Update command/query handler `__init__.py` exports for the four new handlers.

- [ ] **Step 5: Run route tests**

Run:

```bash
pytest tests/unit/api/routes/test_movement_routes.py tests/unit/api/test_app_smoke_routes.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit API work**

```bash
git add src/api/routes/v1/movement.py src/api/schemas/request/movement_requests.py src/api/main.py src/api/dependencies/event_bus.py src/app/handlers/command_handlers/__init__.py src/app/handlers/query_handlers/__init__.py tests/unit/api/routes/test_movement_routes.py
git commit -m "feat: expose movement api"
```

## Task 5: Calorie Balance Integration

**Files:**
- Modify: `src/app/handlers/query_handlers/get_daily_macros_query_handler.py`
- Modify: `src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py`
- Test: `tests/unit/handlers/query_handlers/test_movement_balance_integration.py`

- [ ] **Step 1: Write failing daily balance test**

Add `tests/unit/handlers/query_handlers/test_movement_balance_integration.py`:

```python
from datetime import date

from src.app.handlers.query_handlers.get_nutrition_bulk_query_handler import (
    GetNutritionBulkQueryHandler,
)


def test_bulk_date_summary_uses_net_calories_after_movement():
    handler = GetNutritionBulkQueryHandler()

    result = handler._build_date_summary(
        meals=[],
        target_calories=2000,
        target_macros={"protein": 100, "carbs": 200, "fat": 70},
        movement_kcal=300.0,
    )

    assert result["totals"]["consumed"]["calories"] == -300.0
    assert result["totals"]["remaining"]["calories"] == 2300.0
    assert result["movement_kcal_burned"] == 300.0
```

- [ ] **Step 2: Run balance test to verify RED**

Run:

```bash
pytest tests/unit/handlers/query_handlers/test_movement_balance_integration.py -v
```

Expected: FAIL because `_build_date_summary` does not accept `movement_kcal`.

- [ ] **Step 3: Implement bulk summary adjustment**

Change `_build_date_summary` signature in `get_nutrition_bulk_query_handler.py`:

```python
def _build_date_summary(
    self,
    meals: list,
    target_calories: Optional[float],
    target_macros: Optional[Dict],
    movement_kcal: float = 0.0,
) -> Dict[str, Any]:
```

After `total_calories` calculation:

```python
food_calories = total_calories
net_calories = food_calories - movement_kcal
```

Use `net_calories` for consumed/remaining calories and add:

```python
"food_calories": round(food_calories, 1),
"movement_kcal_burned": round(movement_kcal, 1),
```

- [ ] **Step 4: Fetch movement kcal in bulk handler**

Inside `handle`, after meals are grouped and before the per-date loop, compute a date map:

```python
movement_by_date: Dict[date, float] = {}
current = query.start_date
while current <= query.end_date:
    start_utc, end_utc = self._local_day_utc_range(current, user_tz_str)
    movement_by_date[current] = await uow.movement_entries.sum_included_kcal_for_range(
        query.user_id,
        start_utc,
        end_utc,
    )
    current += timedelta(days=1)
```

Add helper:

```python
def _local_day_utc_range(self, target: date, user_tz_str: str):
    from datetime import datetime, time, timedelta, timezone

    tz = get_zone_info(user_tz_str)
    start_local = datetime.combine(target, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
```

Pass `movement_kcal=movement_by_date.get(current, 0.0)` into `_build_date_summary`.

- [ ] **Step 5: Implement daily macros movement adjustment**

In `get_daily_macros_query_handler.py`, inside the existing UoW and after `target_date` is known:

```python
movement_kcal_burned = 0.0
try:
    from datetime import time, timezone

    start_local = datetime.combine(target_date, time.min, tzinfo=user_tz)
    end_local = start_local + timedelta(days=1)
    movement_kcal_burned = await uow.movement_entries.sum_included_kcal_for_range(
        query.user_id,
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )
except Exception as exc:
    logger.warning("Failed to fetch movement data for user %s: %s", query.user_id, exc)
```

Then before building `result`:

```python
food_calories = total_calories
net_calories = food_calories - movement_kcal_burned
```

Set result fields:

```python
"total_calories": round(net_calories, 1),
"food_calories": round(food_calories, 1),
"movement_kcal_burned": round(movement_kcal_burned, 1),
```

Pass `net_calories` to `_get_weekly_context`.

- [ ] **Step 6: Run balance tests**

Run:

```bash
pytest tests/unit/handlers/query_handlers/test_movement_balance_integration.py tests/unit/handlers/query_handlers/test_daily_macros_uow_consolidation.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit balance integration**

```bash
git add src/app/handlers/query_handlers/get_daily_macros_query_handler.py src/app/handlers/query_handlers/get_nutrition_bulk_query_handler.py tests/unit/handlers/query_handlers/test_movement_balance_integration.py
git commit -m "feat: apply movement calories to nutrition balance"
```

## Task 6: Final Verification

**Files:**
- No new source files.

- [ ] **Step 1: Run focused movement and nutrition tests**

Run:

```bash
pytest tests/unit/domain/services/test_movement_catalog_service.py tests/unit/handlers/command_handlers/test_movement_command_handlers.py tests/unit/handlers/query_handlers/test_movement_query_handlers.py tests/unit/api/routes/test_movement_routes.py tests/unit/handlers/query_handlers/test_movement_balance_integration.py -v
```

Expected: PASS.

- [ ] **Step 2: Run migration graph test**

Run:

```bash
pytest tests/migrations/test_alembic_revision_graph.py -v
```

Expected: PASS.

- [ ] **Step 3: Run existing impacted tests**

Run:

```bash
pytest tests/unit/handlers/query_handlers/test_daily_macros_uow_consolidation.py tests/unit/api/test_app_smoke_routes.py tests/unit/api/test_event_bus_dependency_singletons.py -v
```

Expected: PASS.

- [ ] **Step 4: Run lint/format on touched files**

Run:

```bash
black src/ tests/
flake8 src/
```

Expected: no errors.

- [ ] **Step 5: Final status check**

Run:

```bash
git status --short
```

Expected: only intentional uncommitted files, or clean working tree after final commit.
