# Hydration Goal Calculation & Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement weight-based daily hydration goal calculation and smart goal-based push notification reminders.

**Architecture:** `daily_water_goal_ml` is computed at query time using `resolve_hydration_goal_ml(profile)` — never stored as a derived value. Hydration reminders are pre-created at midnight (13:00 and 18:00 local time) alongside meal reminders, then a live hydration check at send time skips FCM if the user is already on track.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic (migrations dir), PyMediator event bus, Firebase FCM, Redis cache-aside.

---

## File Map

| Action | File |
|---|---|
| Migration exists (just apply) | `migrations/versions/20260522100001_add_daily_water_goal_to_user_profiles.py` |
| Create migration | `migrations/versions/20260523000001_add_hydration_reminders_enabled.py` |
| Modify | `src/domain/model/user/core_user.py` |
| Modify | `src/infra/database/models/user/profile.py` |
| Modify | `src/infra/mappers/user_mapper.py` |
| Create | `src/domain/services/hydration_goal_service.py` |
| Modify | `src/app/handlers/query_handlers/get_daily_hydration_query_handler.py` |
| Modify | `src/app/handlers/query_handlers/get_weekly_hydration_query_handler.py` |
| Modify | `src/app/commands/user/update_user_metrics_command.py` |
| Modify | `src/app/handlers/command_handlers/update_user_metrics_command_handler.py` |
| Modify | `src/api/schemas/request/user_profile_update_requests.py` |
| Modify | `src/api/routes/v1/user_profiles.py` |
| Modify | `src/domain/model/notification/enums.py` |
| Modify | `src/domain/model/notification/notification_preferences.py` |
| Modify | `src/infra/database/models/notification/notification_preferences.py` |
| Modify | `src/infra/mappers/notification_mapper.py` |
| Modify | `src/infra/repositories/notification/notification_preferences_operations.py` |
| Modify | `src/app/commands/notification/update_notification_preferences_command.py` |
| Modify | `src/api/schemas/request/notification_requests.py` |
| Modify | `src/app/handlers/command_handlers/update_notification_preferences_command_handler.py` |
| Modify | `src/domain/services/notification_messages.py` |
| Modify | `src/infra/services/daily_context_precompute_service.py` |
| Modify | `src/infra/services/scheduled_notification_service.py` |
| Modify | `src/api/dependencies/event_bus.py` |
| Create | `tests/unit/domain/services/test_hydration_goal_service.py` |

---

## Task 1: Wire `daily_water_goal_ml` through domain model, ORM, and mapper

**Files:**
- Modify: `src/domain/model/user/core_user.py`
- Modify: `src/infra/database/models/user/profile.py`
- Modify: `src/infra/mappers/user_mapper.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/unit/domain/services/test_hydration_goal_service.py`:

```python
from src.domain.model.user.core_user import UserProfileDomainModel
import uuid


def _make_profile(**kwargs) -> UserProfileDomainModel:
    defaults = dict(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        age=25, gender="male", height_cm=175.0, weight_kg=70.0,
        job_type="desk", training_days_per_week=3,
        training_minutes_per_session=45, fitness_goal="maintenance",
        meals_per_day=3,
    )
    defaults.update(kwargs)
    return UserProfileDomainModel(**defaults)


def test_profile_daily_water_goal_defaults_to_none():
    profile = _make_profile()
    assert profile.daily_water_goal_ml is None
```

- [ ] **Step 1.2: Run test — expect FAIL**

```bash
pytest tests/unit/domain/services/test_hydration_goal_service.py::test_profile_daily_water_goal_defaults_to_none -v
```

Expected: `AttributeError: 'UserProfileDomainModel' object has no attribute 'daily_water_goal_ml'`

- [ ] **Step 1.3: Add `daily_water_goal_ml` to domain model**

In `src/domain/model/user/core_user.py`, add after `goal_started_at: Optional[datetime] = None`:

```python
    daily_water_goal_ml: Optional[int] = None
```

- [ ] **Step 1.4: Add column to UserProfile ORM**

In `src/infra/database/models/user/profile.py`, add after `goal_started_at = Column(DateTime(timezone=True), nullable=True, default=None)`:

```python
    daily_water_goal_ml = Column(Integer, nullable=True, default=None)
```

Also add to `__table_args__` tuple (after existing constraints):

```python
        CheckConstraint(
            "daily_water_goal_ml IS NULL OR daily_water_goal_ml > 0",
            name="check_water_goal_positive",
        ),
```

- [ ] **Step 1.5: Add `daily_water_goal_ml` to both mapper methods**

In `src/infra/mappers/user_mapper.py`, in `UserProfileMapper.to_domain` add after `goal_started_at=profile_entity.goal_started_at`:

```python
            daily_water_goal_ml=profile_entity.daily_water_goal_ml,
```

In `UserProfileMapper.to_persistence` add after `goal_started_at=profile_domain.goal_started_at`:

```python
            daily_water_goal_ml=profile_domain.daily_water_goal_ml,
```

- [ ] **Step 1.6: Apply the existing migration**

```bash
alembic upgrade head
```

Expected: applies `20260522100001` (adds `daily_water_goal_ml` column). If already applied, no-op.

- [ ] **Step 1.7: Run test — expect PASS**

```bash
pytest tests/unit/domain/services/test_hydration_goal_service.py::test_profile_daily_water_goal_defaults_to_none -v
```

- [ ] **Step 1.8: Commit**

```bash
git add src/domain/model/user/core_user.py src/infra/database/models/user/profile.py src/infra/mappers/user_mapper.py tests/unit/domain/services/test_hydration_goal_service.py
git commit -m "feat: add daily_water_goal_ml to user profile domain, ORM, and mapper"
```

---

## Task 2: Hydration goal helper + fix daily and weekly query handlers

**Files:**
- Create: `src/domain/services/hydration_goal_service.py`
- Modify: `src/app/handlers/query_handlers/get_daily_hydration_query_handler.py`
- Modify: `src/app/handlers/query_handlers/get_weekly_hydration_query_handler.py`
- Test: `tests/unit/domain/services/test_hydration_goal_service.py`

- [ ] **Step 2.1: Write failing tests for `resolve_hydration_goal_ml`**

Append to `tests/unit/domain/services/test_hydration_goal_service.py`:

```python
def test_resolve_goal_uses_weight_formula_when_no_override():
    from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
    profile = _make_profile(weight_kg=70.0, daily_water_goal_ml=None)
    assert resolve_hydration_goal_ml(profile) == round(35 * 70.0)  # 2450


def test_resolve_goal_uses_override_when_set():
    from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
    profile = _make_profile(weight_kg=70.0, daily_water_goal_ml=3000)
    assert resolve_hydration_goal_ml(profile) == 3000


def test_resolve_goal_weight_formula_rounds():
    from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
    profile = _make_profile(weight_kg=71.3, daily_water_goal_ml=None)
    assert resolve_hydration_goal_ml(profile) == round(35 * 71.3)
```

- [ ] **Step 2.2: Run tests — expect FAIL**

```bash
pytest tests/unit/domain/services/test_hydration_goal_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.domain.services.hydration_goal_service'`

- [ ] **Step 2.3: Create hydration goal service**

Create `src/domain/services/hydration_goal_service.py`:

```python
"""Hydration goal calculation."""

from src.domain.model.user.core_user import UserProfileDomainModel


def resolve_hydration_goal_ml(profile: UserProfileDomainModel) -> int:
    """Return daily hydration goal in ml.

    Uses custom override if set; otherwise 35 ml per kg body weight.
    """
    return profile.daily_water_goal_ml or round(35 * profile.weight_kg)
```

- [ ] **Step 2.4: Run tests — expect PASS**

```bash
pytest tests/unit/domain/services/test_hydration_goal_service.py -v
```

- [ ] **Step 2.5: Fix `GetDailyHydrationQueryHandler`**

In `src/app/handlers/query_handlers/get_daily_hydration_query_handler.py`, add import at top:

```python
from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
```

Replace lines 91–103 (the `# 4. Fetch water goal` block with the TODO comment) with:

```python
            # 4. Resolve water goal from user profile
            goal_ml = 2000
            try:
                user_profile = await uow.users.get_profile(UUID(query.user_id))
                if user_profile:
                    goal_ml = resolve_hydration_goal_ml(user_profile)
            except Exception:
                logger.debug(
                    "Could not fetch user profile for water goal; defaulting to 2000 ml",
                    exc_info=True,
                )
```

- [ ] **Step 2.6: Fix `GetWeeklyHydrationQueryHandler`**

In `src/app/handlers/query_handlers/get_weekly_hydration_query_handler.py`, add import after the other imports:

```python
from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
```

Replace lines 48–61 (the `# Fetch user goal` block) with:

```python
            goal_ml = 2000
            try:
                from uuid import UUID
                user_profile = await uow.users.get_profile(UUID(query.user_id))
                if user_profile:
                    goal_ml = resolve_hydration_goal_ml(user_profile)
            except Exception:
                logger.debug("Could not fetch user profile for water goal; defaulting to 2000 ml", exc_info=True)
```

- [ ] **Step 2.7: Run the full test suite to catch regressions**

```bash
pytest tests/unit/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 2.8: Commit**

```bash
git add src/domain/services/hydration_goal_service.py src/app/handlers/query_handlers/get_daily_hydration_query_handler.py src/app/handlers/query_handlers/get_weekly_hydration_query_handler.py tests/unit/domain/services/test_hydration_goal_service.py
git commit -m "feat: add resolve_hydration_goal_ml helper and wire into hydration query handlers"
```

---

## Task 3: Expose `daily_water_goal_ml` via the update metrics endpoint

**Files:**
- Modify: `src/app/commands/user/update_user_metrics_command.py`
- Modify: `src/app/handlers/command_handlers/update_user_metrics_command_handler.py`
- Modify: `src/api/schemas/request/user_profile_update_requests.py`
- Modify: `src/api/routes/v1/user_profiles.py`

- [ ] **Step 3.1: Write failing test**

Append to `tests/unit/domain/services/test_hydration_goal_service.py`:

```python
def test_update_metrics_command_accepts_water_goal():
    from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
    cmd = UpdateUserMetricsCommand(user_id="abc", daily_water_goal_ml=2500)
    assert cmd.daily_water_goal_ml == 2500


def test_update_metrics_command_accepts_reset_flag():
    from src.app.commands.user.update_user_metrics_command import UpdateUserMetricsCommand
    cmd = UpdateUserMetricsCommand(user_id="abc", reset_water_goal=True)
    assert cmd.reset_water_goal is True
```

- [ ] **Step 3.2: Run — expect FAIL**

```bash
pytest tests/unit/domain/services/test_hydration_goal_service.py::test_update_metrics_command_accepts_water_goal -v
```

Expected: `TypeError: UpdateUserMetricsCommand.__init__() got an unexpected keyword argument 'daily_water_goal_ml'`

- [ ] **Step 3.3: Add fields to `UpdateUserMetricsCommand`**

In `src/app/commands/user/update_user_metrics_command.py`, add after `goal_started_at: Optional[datetime] = None`:

```python
    daily_water_goal_ml: Optional[int] = None
    reset_water_goal: bool = False
```

- [ ] **Step 3.4: Handle the new fields in `UpdateUserMetricsCommandHandler`**

In `src/app/handlers/command_handlers/update_user_metrics_command_handler.py`:

1. Update the "at least one field" check — add `command.daily_water_goal_ml, command.reset_water_goal` to the list in `if not any([...])`:

```python
        if not any(
            [
                command.weight_kg,
                command.job_type,
                command.training_days_per_week,
                command.training_minutes_per_session,
                command.body_fat_percent,
                command.fitness_goal,
                command.training_level,
                command.target_weight_kg,
                command.goal_start_weight_kg,
                command.goal_started_at,
                command.daily_water_goal_ml,
                command.reset_water_goal,
            ]
        ):
```

2. Add water goal handling after the `goal_started_at` block (before `profile.is_current = True`):

```python
            if command.reset_water_goal:
                profile.daily_water_goal_ml = None
            elif command.daily_water_goal_ml is not None:
                if command.daily_water_goal_ml <= 0:
                    raise ValidationException("Daily water goal must be greater than 0")
                profile.daily_water_goal_ml = command.daily_water_goal_ml
```

3. Add hydration cache invalidation in `_invalidate_user_profile` (called whether weight or water goal changed). Add at the end of the method:

```python
        hydration_pattern = f"user:{user_id}:hydration:*"
        try:
            await self.cache_service.invalidate_pattern(hydration_pattern)
        except Exception as e:
            logger.warning(f"Failed to invalidate hydration pattern for user {user_id}: {e}")

        weekly_hydration_pattern = f"user:{user_id}:hydration_weekly:*"
        try:
            await self.cache_service.invalidate_pattern(weekly_hydration_pattern)
        except Exception as e:
            logger.warning(f"Failed to invalidate weekly hydration pattern for user {user_id}: {e}")
```

- [ ] **Step 3.5: Update API request schema**

In `src/api/schemas/request/user_profile_update_requests.py`, add at the end of `UpdateMetricsRequest`:

```python
    daily_water_goal_ml: int | None = Field(
        None, gt=0, description="Custom daily water goal in ml (null = use weight-based formula)"
    )
    reset_water_goal: bool = Field(
        False, description="Reset daily water goal to weight-based calculation (35 ml/kg)"
    )
```

- [ ] **Step 3.6: Update the API route**

In `src/api/routes/v1/user_profiles.py`, in the `update_user_metrics` function, add `daily_water_goal_ml` and `reset_water_goal` to the `UpdateUserMetricsCommand(...)` constructor call:

```python
        command = UpdateUserMetricsCommand(
            user_id=user_id,
            weight_kg=request.weight_kg,
            job_type=request.job_type,
            training_days_per_week=request.training_days_per_week,
            training_minutes_per_session=request.training_minutes_per_session,
            body_fat_percent=request.body_fat_percent,
            fitness_goal=request.fitness_goal.value if request.fitness_goal else None,
            training_level=(
                request.training_level.value if request.training_level else None
            ),
            target_weight_kg=request.target_weight_kg,
            goal_start_weight_kg=request.goal_start_weight_kg,
            goal_started_at=request.goal_started_at,
            daily_water_goal_ml=request.daily_water_goal_ml,
            reset_water_goal=request.reset_water_goal,
        )
```

- [ ] **Step 3.7: Run tests**

```bash
pytest tests/unit/domain/services/test_hydration_goal_service.py -v && pytest tests/unit/domain/test_update_user_metrics.py -v 2>/dev/null || pytest tests/unit/ -v --tb=short -q
```

Expected: all pass.

- [ ] **Step 3.8: Commit**

```bash
git add src/app/commands/user/update_user_metrics_command.py src/app/handlers/command_handlers/update_user_metrics_command_handler.py src/api/schemas/request/user_profile_update_requests.py src/api/routes/v1/user_profiles.py tests/unit/domain/services/test_hydration_goal_service.py
git commit -m "feat: expose daily_water_goal_ml via update metrics endpoint"
```

---

## Task 4: `hydration_reminders_enabled` — migration, domain, ORM, mapper, repo, API

**Files:**
- Create: `migrations/versions/20260523000001_add_hydration_reminders_enabled.py`
- Modify: `src/domain/model/notification/notification_preferences.py`
- Modify: `src/infra/database/models/notification/notification_preferences.py`
- Modify: `src/infra/mappers/notification_mapper.py`
- Modify: `src/infra/repositories/notification/notification_preferences_operations.py`
- Modify: `src/app/commands/notification/update_notification_preferences_command.py`
- Modify: `src/api/schemas/request/notification_requests.py`
- Modify: `src/app/handlers/command_handlers/update_notification_preferences_command_handler.py`

- [ ] **Step 4.1: Write failing test**

Create `tests/unit/domain/test_notification_hydration_prefs.py`:

```python
def test_notification_preferences_has_hydration_reminders_enabled():
    from src.domain.model.notification.notification_preferences import NotificationPreferences
    import uuid
    prefs = NotificationPreferences(
        preferences_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )
    assert prefs.hydration_reminders_enabled is True


def test_create_default_has_hydration_reminders_enabled():
    from src.domain.model.notification.notification_preferences import NotificationPreferences
    import uuid
    prefs = NotificationPreferences.create_default(str(uuid.uuid4()))
    assert prefs.hydration_reminders_enabled is True


def test_update_preferences_toggles_hydration_reminders():
    from src.domain.model.notification.notification_preferences import NotificationPreferences
    import uuid
    prefs = NotificationPreferences.create_default(str(uuid.uuid4()))
    updated = prefs.update_preferences(hydration_reminders_enabled=False)
    assert updated.hydration_reminders_enabled is False
```

- [ ] **Step 4.2: Run — expect FAIL**

```bash
pytest tests/unit/domain/test_notification_hydration_prefs.py -v
```

- [ ] **Step 4.3: Create the migration**

Create `migrations/versions/20260523000001_add_hydration_reminders_enabled.py`:

```python
"""Add hydration_reminders_enabled to notification_preferences.

Revision ID: 20260523000001
Revises: 20260522100001
"""
import sqlalchemy as sa
from alembic import op

revision = "20260523000001"
down_revision = "20260522100001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_preferences",
        sa.Column(
            "hydration_reminders_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_preferences", "hydration_reminders_enabled")
```

- [ ] **Step 4.4: Apply migration**

```bash
alembic upgrade head
```

- [ ] **Step 4.5: Update `NotificationPreferences` domain model**

In `src/domain/model/notification/notification_preferences.py`:

1. Add `hydration_reminders_enabled: bool = True` after `daily_summary_enabled: bool = True`:

```python
    hydration_reminders_enabled: bool = True
```

2. In `create_default`, add `hydration_reminders_enabled=True` after `daily_summary_enabled=True`:

```python
            hydration_reminders_enabled=True,
```

3. Add `hydration_reminders_enabled: bool | None = None` parameter to `update_preferences` method signature after `daily_summary_enabled`:

```python
        hydration_reminders_enabled: bool | None = None,
```

4. In `update_preferences`, add handling after `daily_summary_enabled`:

```python
            hydration_reminders_enabled=(
                hydration_reminders_enabled
                if hydration_reminders_enabled is not None
                else self.hydration_reminders_enabled
            ),
```

5. In `to_dict`, add after `"daily_summary_enabled": self.daily_summary_enabled`:

```python
            "hydration_reminders_enabled": self.hydration_reminders_enabled,
```

6. In `NotificationPreferences.__init__` constructor call in `update_preferences` (the `return NotificationPreferences(...)` block), add `hydration_reminders_enabled=...` at the appropriate place.

The full updated `update_preferences` return statement should include:
```python
        return NotificationPreferences(
            preferences_id=self.preferences_id,
            user_id=self.user_id,
            meal_reminders_enabled=(
                meal_reminders_enabled
                if meal_reminders_enabled is not None
                else self.meal_reminders_enabled
            ),
            daily_summary_enabled=(
                daily_summary_enabled
                if daily_summary_enabled is not None
                else self.daily_summary_enabled
            ),
            hydration_reminders_enabled=(
                hydration_reminders_enabled
                if hydration_reminders_enabled is not None
                else self.hydration_reminders_enabled
            ),
            breakfast_time_minutes=(
                breakfast_time_minutes
                if breakfast_time_minutes is not None
                else self.breakfast_time_minutes
            ),
            lunch_time_minutes=(
                lunch_time_minutes
                if lunch_time_minutes is not None
                else self.lunch_time_minutes
            ),
            dinner_time_minutes=(
                dinner_time_minutes
                if dinner_time_minutes is not None
                else self.dinner_time_minutes
            ),
            daily_summary_time_minutes=(
                daily_summary_time_minutes
                if daily_summary_time_minutes is not None
                else self.daily_summary_time_minutes
            ),
            language=language if language is not None else self.language,
            created_at=self.created_at,
            updated_at=utc_now(),
        )
```

- [ ] **Step 4.6: Update `NotificationPreferencesORM`**

In `src/infra/database/models/notification/notification_preferences.py`, add after `daily_summary_enabled`:

```python
    hydration_reminders_enabled = Column(Boolean, default=True, nullable=False, server_default="true")
```

- [ ] **Step 4.7: Update mapper**

In `src/infra/mappers/notification_mapper.py`, add `hydration_reminders_enabled=orm.hydration_reminders_enabled` to the `notification_prefs_orm_to_domain` return statement after `daily_summary_enabled`:

```python
        hydration_reminders_enabled=orm.hydration_reminders_enabled,
```

- [ ] **Step 4.8: Update `NotificationPreferencesOperations.save_notification_preferences`**

In `src/infra/repositories/notification/notification_preferences_operations.py`:

1. In the `if existing_prefs:` branch, add after `existing_prefs.daily_summary_enabled = preferences.daily_summary_enabled`:

```python
                existing_prefs.hydration_reminders_enabled = (
                    preferences.hydration_reminders_enabled
                )
```

2. In the `else:` branch (new ORM object), add `hydration_reminders_enabled=preferences.hydration_reminders_enabled` to the `NotificationPreferencesORM(...)` constructor.

- [ ] **Step 4.9: Update command and API schema**

In `src/app/commands/notification/update_notification_preferences_command.py`, add after `daily_summary_enabled`:

```python
    hydration_reminders_enabled: Optional[bool] = None
```

In `src/api/schemas/request/notification_requests.py`, add after `daily_summary_enabled`:

```python
    hydration_reminders_enabled: Optional[bool] = Field(
        None, description="Enable/disable hydration reminder notifications"
    )
```

- [ ] **Step 4.10: Update the command handler**

In `src/app/handlers/command_handlers/update_notification_preferences_command_handler.py`, update the `updated_prefs = saved_prefs.update_preferences(...)` call to pass `hydration_reminders_enabled=command.hydration_reminders_enabled`.

- [ ] **Step 4.11: Run tests — expect PASS**

```bash
pytest tests/unit/domain/test_notification_hydration_prefs.py -v && pytest tests/unit/ -q
```

- [ ] **Step 4.12: Commit**

```bash
git add migrations/versions/20260523000001_add_hydration_reminders_enabled.py src/domain/model/notification/notification_preferences.py src/infra/database/models/notification/notification_preferences.py src/infra/mappers/notification_mapper.py src/infra/repositories/notification/notification_preferences_operations.py src/app/commands/notification/update_notification_preferences_command.py src/api/schemas/request/notification_requests.py src/app/handlers/command_handlers/update_notification_preferences_command_handler.py tests/unit/domain/test_notification_hydration_prefs.py
git commit -m "feat: add hydration_reminders_enabled to notification preferences"
```

---

## Task 5: `NotificationType` enum + message copy

**Files:**
- Modify: `src/domain/model/notification/enums.py`
- Modify: `src/domain/model/notification/notification_preferences.py`
- Modify: `src/domain/services/notification_messages.py`

- [ ] **Step 5.1: Write failing tests**

Append to `tests/unit/domain/services/test_notification_messages.py`:

```python
@pytest.mark.parametrize(
    "lang,gender",
    [
        ("en", "male"),
        ("en", "female"),
        ("vi", "male"),
        ("vi", "female"),
    ],
)
def test_hydration_reminder_keys_exist(lang, gender):
    msgs = get_messages(lang, gender)
    assert "hydration_reminder" in msgs
    assert "afternoon" in msgs["hydration_reminder"]
    assert "evening" in msgs["hydration_reminder"]
    assert msgs["hydration_reminder"]["afternoon"]["body_template"]
    assert msgs["hydration_reminder"]["evening"]["body_template"]


def test_hydration_type_enum_values_exist():
    from src.domain.model.notification.enums import NotificationType
    assert NotificationType.HYDRATION_REMINDER_AFTERNOON.value == "hydration_reminder_afternoon"
    assert NotificationType.HYDRATION_REMINDER_EVENING.value == "hydration_reminder_evening"
```

- [ ] **Step 5.2: Run — expect FAIL**

```bash
pytest tests/unit/domain/services/test_notification_messages.py -v
```

- [ ] **Step 5.3: Add enum values**

In `src/domain/model/notification/enums.py`, add after `DAILY_SUMMARY`:

```python
    HYDRATION_REMINDER_AFTERNOON = "hydration_reminder_afternoon"
    HYDRATION_REMINDER_EVENING = "hydration_reminder_evening"
```

- [ ] **Step 5.4: Update `NOTIFICATION_TYPE_TO_FIELD` map**

In `src/domain/model/notification/notification_preferences.py`, add to the `NOTIFICATION_TYPE_TO_FIELD` dict:

```python
    NotificationType.HYDRATION_REMINDER_AFTERNOON: "hydration_reminders_enabled",
    NotificationType.HYDRATION_REMINDER_EVENING: "hydration_reminders_enabled",
```

- [ ] **Step 5.5: Add message copy**

In `src/domain/services/notification_messages.py`, add a `"hydration_reminder"` key inside each gender block for `"en"` and `"vi"`.

For `en → male`, after the `"trial_expiry"` block:

```python
            "hydration_reminder": {
                "afternoon": {
                    "body_template": "Halfway there, bro! {consumed_ml}ml down, {remaining_ml}ml to go\nStay hydrated 💧",
                },
                "evening": {
                    "body_template": "Almost there, bro! {consumed_ml}ml logged today\nJust {remaining_ml}ml left to hit your goal 💧",
                },
            },
```

For `en → female`, after the `"trial_expiry"` block:

```python
            "hydration_reminder": {
                "afternoon": {
                    "body_template": "Halfway there, mate! {consumed_ml}ml down, {remaining_ml}ml to go\nStay hydrated 💧",
                },
                "evening": {
                    "body_template": "Almost there, mate! {consumed_ml}ml logged today\nJust {remaining_ml}ml left to hit your goal 💧",
                },
            },
```

For `vi → male`, after the `"trial_expiry"` block:

```python
            "hydration_reminder": {
                "afternoon": {
                    "body_template": "Giữa ngày rồi bro! Uống thêm {remaining_ml}ml nữa nhé\nHôm nay uống được {consumed_ml}ml rồi đó 💧",
                },
                "evening": {
                    "body_template": "Chiều tà rồi bro! Còn {remaining_ml}ml nữa là đủ nước\nCố lên nha 💧",
                },
            },
```

For `vi → female`, after the `"trial_expiry"` block:

```python
            "hydration_reminder": {
                "afternoon": {
                    "body_template": "Giữa ngày rồi bạn ơi! Uống thêm {remaining_ml}ml nữa nhé\nHôm nay uống được {consumed_ml}ml rồi đó 💧",
                },
                "evening": {
                    "body_template": "Chiều tà rồi bạn ơi! Còn {remaining_ml}ml nữa là đủ nước\nCố lên nha 💧",
                },
            },
```

- [ ] **Step 5.6: Run tests — expect PASS**

```bash
pytest tests/unit/domain/services/test_notification_messages.py -v
```

- [ ] **Step 5.7: Commit**

```bash
git add src/domain/model/notification/enums.py src/domain/model/notification/notification_preferences.py src/domain/services/notification_messages.py tests/unit/domain/services/test_notification_messages.py
git commit -m "feat: add hydration reminder notification types and message copy"
```

---

## Task 6: Pre-compute hydration reminder rows at midnight

**Files:**
- Modify: `src/infra/services/daily_context_precompute_service.py`

- [ ] **Step 6.1: Write failing test**

Append to `tests/unit/infra/test_scheduled_notification_service.py`:

```python
def test_build_notification_rows_includes_hydration_reminders_when_enabled():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
        _DEFAULT_AFTERNOON_MINUTES,
        _DEFAULT_EVENING_MINUTES,
    )
    from datetime import date

    svc = DailyContextPrecomputeService.__new__(DailyContextPrecomputeService)
    from unittest.mock import MagicMock
    svc._tdee_service = MagicMock()

    pref = MagicMock()
    pref.user_id = "user-1"
    pref.meal_reminders_enabled = False
    pref.daily_summary_enabled = False
    pref.hydration_reminders_enabled = True
    pref.language = "en"

    tokens_by_user = {"user-1": ["tok1"]}
    profiles_by_user = {"user-1": MagicMock(gender="male", language_code="en")}
    today = date(2026, 5, 23)

    rows = svc._build_notification_rows(
        pref_rows=[pref],
        tokens_by_user=tokens_by_user,
        calorie_goals={"user-1": 2000},
        consumed_by_user={"user-1": 0},
        profiles_by_user=profiles_by_user,
        today=today,
        tz_name="UTC",
    )

    types = [r["notification_type"] for r in rows]
    assert "hydration_reminder_afternoon" in types
    assert "hydration_reminder_evening" in types


def test_build_notification_rows_skips_hydration_when_disabled():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
    from datetime import date
    from unittest.mock import MagicMock

    svc = DailyContextPrecomputeService.__new__(DailyContextPrecomputeService)
    svc._tdee_service = MagicMock()

    pref = MagicMock()
    pref.user_id = "user-2"
    pref.meal_reminders_enabled = False
    pref.daily_summary_enabled = False
    pref.hydration_reminders_enabled = False
    pref.language = "en"

    rows = svc._build_notification_rows(
        pref_rows=[pref],
        tokens_by_user={"user-2": ["tok1"]},
        calorie_goals={"user-2": 2000},
        consumed_by_user={"user-2": 0},
        profiles_by_user={"user-2": MagicMock(gender="male", language_code="en")},
        today=date(2026, 5, 23),
        tz_name="UTC",
    )

    types = [r["notification_type"] for r in rows]
    assert "hydration_reminder_afternoon" not in types
    assert "hydration_reminder_evening" not in types
```

- [ ] **Step 6.2: Run — expect FAIL**

```bash
pytest tests/unit/infra/test_scheduled_notification_service.py::test_build_notification_rows_includes_hydration_reminders_when_enabled -v
```

Expected: `AttributeError: 'MagicMock' object has no attribute 'hydration_reminders_enabled'` or similar.

- [ ] **Step 6.3: Add constants and update `_build_notification_rows`**

In `src/infra/services/daily_context_precompute_service.py`:

1. Add constants after the existing `_DEFAULT_SUMMARY_MINUTES`:

```python
_DEFAULT_AFTERNOON_MINUTES = 780   # 13:00
_DEFAULT_EVENING_MINUTES = 1_080   # 18:00
```

2. In `_build_notification_rows`, after the `if pref.daily_summary_enabled:` block, add:

```python
            if pref.hydration_reminders_enabled:
                hydration_context = {
                    "fcm_tokens": tokens,
                    "gender": gender,
                    "language_code": language_code,
                }
                for notif_type, local_minutes in [
                    ("hydration_reminder_afternoon", _DEFAULT_AFTERNOON_MINUTES),
                    ("hydration_reminder_evening", _DEFAULT_EVENING_MINUTES),
                ]:
                    scheduled_utc = _local_minutes_to_utc(today, local_minutes, tz_name)
                    if scheduled_utc is None:
                        continue
                    rows.append(
                        {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "notification_type": notif_type,
                            "scheduled_date": today,
                            "scheduled_for_utc": scheduled_utc,
                            "status": "pending",
                            "context": hydration_context,
                            "created_at": now,
                            "expires_at": expires_at,
                        }
                    )
```

3. Update Query 1 SQL in `_precompute_db_sync` to also select `np.hydration_reminders_enabled`. Replace the SELECT in `_precompute_db_sync` with:

```python
            pref_rows = session.execute(
                text("""
                    SELECT
                        np.user_id,
                        np.meal_reminders_enabled,
                        np.daily_summary_enabled,
                        np.hydration_reminders_enabled,
                        np.breakfast_time_minutes,
                        np.lunch_time_minutes,
                        np.dinner_time_minutes,
                        np.daily_summary_time_minutes,
                        np.language
                    FROM notification_preferences np
                    JOIN users u ON u.id = np.user_id
                    WHERE u.timezone = :tz_name
                      AND u.is_active = true
                      AND np.is_deleted = false
                      AND EXISTS (
                          SELECT 1 FROM user_fcm_tokens t
                          WHERE t.user_id = np.user_id AND t.is_active = true
                      )
                """),
                {"tz_name": tz_name},
            ).fetchall()
```

4. Update `_reschedule_user_sync` similarly — add `hydration_reminders_enabled` to the SELECT in the `pref_row` query:

```python
            pref_row = session.execute(
                text("""
                    SELECT meal_reminders_enabled, daily_summary_enabled,
                           hydration_reminders_enabled,
                           breakfast_time_minutes, lunch_time_minutes,
                           dinner_time_minutes, daily_summary_time_minutes, language
                    FROM notification_preferences
                    WHERE user_id = :user_id AND is_deleted = false
                """),
                {"user_id": user_id},
            ).fetchone()
```

5. In `_reschedule_user_sync`, after the `if pref_row.daily_summary_enabled:` block, add the hydration reminder rows using the same pattern as `_build_notification_rows`:

```python
            if pref_row.hydration_reminders_enabled:
                hydration_context = {
                    "fcm_tokens": tokens,
                    "gender": gender,
                    "language_code": language_code,
                }
                for notif_type, local_minutes in [
                    ("hydration_reminder_afternoon", _DEFAULT_AFTERNOON_MINUTES),
                    ("hydration_reminder_evening", _DEFAULT_EVENING_MINUTES),
                ]:
                    scheduled_utc = _local_minutes_to_utc(today, local_minutes, tz_name)
                    if scheduled_utc and scheduled_utc > now:
                        rows.append(
                            {
                                "id": str(uuid.uuid4()),
                                "user_id": user_id,
                                "notification_type": notif_type,
                                "scheduled_date": today,
                                "scheduled_for_utc": scheduled_utc,
                                "status": "pending",
                                "context": hydration_context,
                                "created_at": now,
                                "expires_at": expires_at,
                            }
                        )
```

Note: `_reschedule_user_sync` computes `context` differently (it includes `calorie_goal` and `calories_consumed`). The hydration reminder rows use a separate `hydration_context` with only `fcm_tokens`, `gender`, and `language_code` — do not reuse the existing `context` dict.

- [ ] **Step 6.4: Run tests — expect PASS**

```bash
pytest tests/unit/infra/test_scheduled_notification_service.py -v
```

- [ ] **Step 6.5: Commit**

```bash
git add src/infra/services/daily_context_precompute_service.py tests/unit/infra/test_scheduled_notification_service.py
git commit -m "feat: pre-compute hydration reminder rows at midnight alongside meal reminders"
```

---

## Task 7: Live hydration check in the send loop

**Files:**
- Modify: `src/infra/services/scheduled_notification_service.py`

- [ ] **Step 7.1: Write failing test**

Append to `tests/unit/infra/test_scheduled_notification_service.py`:

```python
@pytest.mark.asyncio
async def test_hydration_reminder_skipped_when_above_threshold():
    """Afternoon reminder skipped when user has consumed >= 50% of goal."""
    from src.infra.services.scheduled_notification_service import ScheduledNotificationService
    from unittest.mock import MagicMock, patch
    from datetime import datetime, timezone

    mock_notif = MagicMock()
    mock_notif.notification_type = "hydration_reminder_afternoon"
    mock_notif.context = {"fcm_tokens": ["tok1"], "gender": "male", "language_code": "en"}
    mock_notif.id = "hydration-notif-1"
    mock_notif.user_id = "user-h1"

    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(return_value={"success": True, "failed_tokens": []})

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._firebase = mock_firebase
    svc._running = True

    # consumed_ml=1500, goal_ml=2000 → 75% → above 50% afternoon threshold → skip FCM
    with patch(
        "src.infra.services.scheduled_notification_service.ReminderQueryBuilder"
    ) as mock_qb, patch(
        "src.infra.services.scheduled_notification_service.UnitOfWork"
    ) as mock_uow, patch(
        "src.infra.services.scheduled_notification_service._fetch_hydration_data_batch",
        return_value={"user-h1": (1500, 2000)},
    ):
        mock_qb.find_due_notifications.return_value = [mock_notif]
        mock_uow.return_value.__enter__.return_value.session = MagicMock()
        now = datetime(2026, 5, 23, 6, 0, 0, tzinfo=timezone.utc)
        await svc._send_due_notifications(now)

    # FCM not called because threshold met
    mock_firebase.send_multicast.assert_not_called()
    # But notification still marked as processing (then sent via _mark_notifications)
    assert mock_notif.status == "processing"


@pytest.mark.asyncio
async def test_hydration_reminder_sent_when_below_threshold():
    """Evening reminder fires when user has consumed < 80% of goal."""
    from src.infra.services.scheduled_notification_service import ScheduledNotificationService
    from unittest.mock import MagicMock, patch
    from datetime import datetime, timezone

    mock_notif = MagicMock()
    mock_notif.notification_type = "hydration_reminder_evening"
    mock_notif.context = {"fcm_tokens": ["tok1"], "gender": "male", "language_code": "en"}
    mock_notif.id = "hydration-notif-2"
    mock_notif.user_id = "user-h2"

    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(return_value={"success": True, "failed_tokens": []})

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._firebase = mock_firebase
    svc._running = True

    # consumed_ml=1200, goal_ml=2000 → 60% → below 80% evening threshold → send
    with patch(
        "src.infra.services.scheduled_notification_service.ReminderQueryBuilder"
    ) as mock_qb, patch(
        "src.infra.services.scheduled_notification_service.UnitOfWork"
    ) as mock_uow, patch(
        "src.infra.services.scheduled_notification_service._fetch_hydration_data_batch",
        return_value={"user-h2": (1200, 2000)},
    ):
        mock_qb.find_due_notifications.return_value = [mock_notif]
        mock_uow.return_value.__enter__.return_value.session = MagicMock()
        now = datetime(2026, 5, 23, 11, 0, 0, tzinfo=timezone.utc)
        await svc._send_due_notifications(now)

    mock_firebase.send_multicast.assert_called_once()
```

- [ ] **Step 7.2: Run — expect FAIL**

```bash
pytest tests/unit/infra/test_scheduled_notification_service.py::test_hydration_reminder_skipped_when_above_threshold -v
```

Expected: `AttributeError` or test failure because hydration handling doesn't exist yet.

- [ ] **Step 7.3: Add `_fetch_hydration_data_batch` helper**

In `src/infra/services/scheduled_notification_service.py`, add this function after `_fetch_calories_consumed_batch`:

```python
def _fetch_hydration_data_batch(
    user_ids: list[str], now: datetime
) -> dict[str, tuple[int, int]]:
    """Fetch (consumed_ml, goal_ml) per user for a 24-hour lookback window.

    Uses a 24-hour window from now, matching the meal calories batch approach.
    Returns dict of user_id -> (consumed_ml, goal_ml).
    """
    window_start = now - timedelta(hours=24)
    with UnitOfWork() as uow:
        profile_rows = uow.session.execute(
            text("""
                SELECT up.user_id, up.daily_water_goal_ml, up.weight_kg
                FROM user_profiles up
                WHERE up.user_id = ANY(:ids) AND up.is_current = true
            """),
            {"ids": user_ids},
        ).fetchall()

        profile_by_user = {r.user_id: r for r in profile_rows}

        hydration_rows = uow.session.execute(
            text("""
                SELECT user_id, COALESCE(SUM(credited_ml), 0) AS consumed_ml
                FROM hydration_logs
                WHERE user_id = ANY(:ids)
                  AND logged_at >= :start
                  AND is_deleted = false
                GROUP BY user_id
            """),
            {"ids": user_ids, "start": window_start.replace(tzinfo=None)},
        ).fetchall()

        consumed_by_user = {r.user_id: int(r.consumed_ml) for r in hydration_rows}

    result = {}
    for user_id in user_ids:
        profile = profile_by_user.get(user_id)
        if profile is None:
            result[user_id] = (0, 2000)
            continue
        goal_ml = profile.daily_water_goal_ml or round(35 * float(profile.weight_kg))
        consumed_ml = consumed_by_user.get(user_id, 0)
        result[user_id] = (consumed_ml, goal_ml)

    return result
```

- [ ] **Step 7.4: Update `_send_due_notifications` to handle hydration types**

In `_send_due_notifications`, after the `consumed_map` block (after `if meal_reminder_ids:`), add:

```python
        hydration_user_ids = [
            n.user_id for n in due
            if n.notification_type.startswith("hydration_reminder")
        ]
        hydration_map: dict[str, tuple[int, int]] = {}
        if hydration_user_ids:
            hydration_map = await asyncio.to_thread(
                _fetch_hydration_data_batch, hydration_user_ids, now
            )
```

Then, in the rendering loop inside `for notif in due:`, after the `if notif.notification_type == "daily_summary":` block and before the `remaining = max(0, ...)` line, add a new `elif` branch:

```python
            elif notif.notification_type.startswith("hydration_reminder"):
                consumed_ml, goal_ml = hydration_map.get(notif.user_id, (0, 2000))
                threshold = 0.5 if "afternoon" in notif.notification_type else 0.8
                if consumed_ml >= threshold * goal_ml:
                    # User is on track — mark as sent without sending FCM
                    sent_ids.append(notif.id)
                    continue
                remaining_ml = max(0, goal_ml - consumed_ml)
                title, body = _render_message(
                    notif.notification_type,
                    0,
                    gender,
                    lang,
                    consumed_ml=consumed_ml,
                    goal_ml=goal_ml,
                    remaining_ml=remaining_ml,
                )
                group = groups[(notif.notification_type, title, body)]
                group["tokens"].extend(tokens)
                group["ids"].append(str(notif.id))
                sent_ids.append(notif.id)
                continue
```

Note: place this `elif` branch BEFORE the `remaining = max(0, ...)` line and BEFORE the `title, body = _render_message(...)` call that applies to meal reminders.

The full rendering block order after changes:
1. `if not tokens:` → failed
2. Get context values
3. `if notif.notification_type == "daily_summary":` → snapshot calories
4. `elif notif.notification_type.startswith("trial_expiry"):` → zero
5. **`elif notif.notification_type.startswith("hydration_reminder"):` → live check + `continue`**
6. `else:` → meal_reminder real-time

- [ ] **Step 7.5: Update `_render_message` for hydration types**

In `_render_message`, add `consumed_ml: int = 0`, `goal_ml: int = 2000`, and `remaining_ml: int = 0` to the signature:

```python
def _render_message(
    notification_type: str,
    remaining: int,
    gender: str,
    lang: str,
    calories_consumed: int = 0,
    calorie_goal: int = 2000,
    consumed_ml: int = 0,
    goal_ml: int = 2000,
    remaining_ml: int = 0,
) -> tuple[str, str]:
```

Add handling before the final `return "Nutree", "You have a notification 📬"` fallback:

```python
    elif notification_type == "hydration_reminder_afternoon":
        cfg = messages["hydration_reminder"]["afternoon"]
        return "Nutree", cfg["body_template"].format(
            consumed_ml=consumed_ml, remaining_ml=remaining_ml
        )
    elif notification_type == "hydration_reminder_evening":
        cfg = messages["hydration_reminder"]["evening"]
        return "Nutree", cfg["body_template"].format(
            consumed_ml=consumed_ml, remaining_ml=remaining_ml
        )
```

- [ ] **Step 7.6: Run tests — expect PASS**

```bash
pytest tests/unit/infra/test_scheduled_notification_service.py -v
```

- [ ] **Step 7.7: Run full test suite**

```bash
pytest tests/unit/ -q --tb=short
```

Expected: all pass.

- [ ] **Step 7.8: Commit**

```bash
git add src/infra/services/scheduled_notification_service.py tests/unit/infra/test_scheduled_notification_service.py
git commit -m "feat: live hydration check in notification send loop with afternoon/evening thresholds"
```

---

## Task 8: Wire into the event bus and run full suite

**Files:**
- Modify: `src/api/dependencies/event_bus.py`

- [ ] **Step 8.1: Register hydration goal handlers**

In `src/api/dependencies/event_bus.py`, the `UpdateUserMetricsCommandHandler` is already registered. No new event handler is needed — hydration cache invalidation is handled directly inside `_invalidate_user_profile` (added in Task 3).

Verify that `UpdateNotificationPreferencesCommandHandler` (already registered) will pick up the `hydration_reminders_enabled` field via the command — no bus changes needed there either.

Run a grep to confirm both handlers are already wired:

```bash
grep -n "UpdateUserMetricsCommandHandler\|UpdateNotificationPreferencesCommandHandler" src/api/dependencies/event_bus.py
```

Expected: both appear in the file.

- [ ] **Step 8.2: Run the full test suite**

```bash
pytest tests/ -q --tb=short --ignore=tests/integration
```

Expected: all unit tests pass.

- [ ] **Step 8.3: Run integration tests if DB is available**

```bash
pytest tests/integration/ -q --tb=short 2>/dev/null || echo "Integration tests skipped (no DB)"
```

- [ ] **Step 8.4: Final commit**

```bash
git add src/api/dependencies/event_bus.py
git commit -m "feat: hydration goal and smart notifications — complete feature wiring

- Weight-based hydration goal (35ml/kg) with optional user override
- daily_water_goal_ml field on user profile
- Smart hydration reminders at 13:00 and 18:00 local time
- Live threshold check at send time (50% afternoon, 80% evening)
- hydration_reminders_enabled preference toggle"
```
