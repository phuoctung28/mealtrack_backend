# Render Cron Notification Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all scheduled notification work (FCM push + lifecycle emails) out of the FastAPI web process into two dedicated Render Cron Job services, eliminating the CPU spike caused by in-process schedulers.

**Architecture:** Two cron scripts (`src/cron/push.py`, `src/cron/email.py`) run as separate Render services on `*/2 * * * *` and `0 9 * * *` schedules respectively. Each script starts, completes its work, and exits — no persistent loops. The web service (`main.py`) becomes a pure request handler with no background tasks.

**Tech Stack:** Python 3.11, asyncio, SQLAlchemy (NullPool via existing Neon config), Firebase Admin SDK, Redis (2 connections max in cron), Resend (email), Sentry, Render cron YAML.

**Spec:** `docs/superpowers/specs/2026-05-21-render-cron-notifications-design.md`

**Run tests with:** `.venv/bin/python -m pytest <path> -v`

---

## File Map

```
NEW
  src/cron/__init__.py                         — empty package marker
  src/cron/push.py                             — push cron: Phase 1 precompute + Phase 2 trial rows + Phase 3 FCM
  src/cron/email.py                            — email cron: re-engagement + trial-expiring emails
  tests/unit/cron/__init__.py                  — test package marker
  tests/unit/cron/test_push_cron.py            — unit tests for push cron
  tests/unit/cron/test_email_cron.py           — unit tests for email cron
  render.yaml                                  — Render infrastructure definition

MODIFIED
  src/api/main.py                              — remove scheduler + email startup/shutdown from lifespan
  src/api/base_dependencies.py                 — remove scheduler singleton functions
  tests/unit/api/test_api_main_firebase_and_lifespan.py  — update stubs + remove scheduler test
```

---

## Task 1: Create cron package skeleton

**Files:**
- Create: `src/cron/__init__.py`
- Create: `tests/unit/cron/__init__.py`

- [ ] **Step 1: Create the package files**

```bash
mkdir -p src/cron tests/unit/cron
touch src/cron/__init__.py tests/unit/cron/__init__.py
```

- [ ] **Step 2: Verify Python sees both packages**

```bash
.venv/bin/python -c "import src.cron; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/cron/__init__.py tests/unit/cron/__init__.py
git commit -m "chore: add cron package skeleton"
```

---

## Task 2: Strip in-process scheduler from web service

**Files:**
- Modify: `src/api/main.py`
- Modify: `src/api/base_dependencies.py`
- Modify: `tests/unit/api/test_api_main_firebase_and_lifespan.py`

- [ ] **Step 1: Update the lifespan fixture — write failing expectation first**

Open `tests/unit/api/test_api_main_firebase_and_lifespan.py`.

Replace the entire `_patch_lifespan_side_effects` function and `fresh_main` fixture, and remove `test_lifespan_scheduled_start_failure_still_starts_api`, so the file looks like this from line 1:

```python
"""Cover src.api.main: Firebase init branches and lifespan error paths."""
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _reload_main():
    """Fresh import so initialize_firebase is the real function (not stubbed by other tests)."""
    sys.modules.pop("src.api.main", None)
    return importlib.import_module("src.api.main")


def _patch_lifespan_side_effects(main_mod):
    main_mod.initialize_firebase = lambda: None  # type: ignore[assignment]

    async def _noop():
        return None

    main_mod.initialize_cache_layer = _noop  # type: ignore[assignment]
    main_mod.shutdown_cache_layer = _noop  # type: ignore[assignment]
    # Note: no scheduler stub — scheduler removed from lifespan


@pytest.fixture
def fresh_main(monkeypatch, tmp_path):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("FAIL_ON_CACHE_ERROR", raising=False)
    monkeypatch.delenv("FIREBASE_CREDENTIALS", raising=False)
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    sys.modules.pop("src.api.main", None)
    m = importlib.import_module("src.api.main")
    _patch_lifespan_side_effects(m)
    return m


def test_lifespan_firebase_failure_propagates(monkeypatch, fresh_main):
    fresh_main.initialize_firebase = lambda: (_ for _ in ()).throw(  # type: ignore[assignment]
        RuntimeError("firebase down")
    )
    with pytest.raises(RuntimeError, match="firebase down"):
        with TestClient(fresh_main.app):
            pass


def test_lifespan_cache_failure_raises_when_env_true(monkeypatch, fresh_main):
    monkeypatch.setenv("FAIL_ON_CACHE_ERROR", "true")

    async def boom():
        raise RuntimeError("cache")

    fresh_main.initialize_cache_layer = boom  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="cache"):
        with TestClient(fresh_main.app):
            pass


def test_initialize_firebase_already_initialized(monkeypatch):
    main = _reload_main()

    monkeypatch.setattr(main.firebase_admin, "get_app", lambda: MagicMock(name="app"))
    main.initialize_firebase()


def test_initialize_firebase_default_credentials(monkeypatch):
    main = _reload_main()

    def _not_init():
        raise ValueError("not init")

    monkeypatch.setattr(main.firebase_admin, "get_app", _not_init)
    monkeypatch.delenv("FIREBASE_CREDENTIALS", raising=False)
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    init = MagicMock()
    monkeypatch.setattr(main.firebase_admin, "initialize_app", init)
    main.initialize_firebase()
    init.assert_called_once()


def test_initialize_firebase_from_json_string(monkeypatch):
    main = _reload_main()

    def _not_init():
        raise ValueError("not init")

    monkeypatch.setattr(main.firebase_admin, "get_app", _not_init)
    monkeypatch.setenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON",
        '{"type": "service_account", "project_id": "test"}',
    )
    init = MagicMock()
    monkeypatch.setattr(main.firebase_admin, "initialize_app", init)
    monkeypatch.setattr(main.credentials, "Certificate", MagicMock(return_value="cred"))
    main.initialize_firebase()
    init.assert_called_once_with("cred")


def test_initialize_firebase_invalid_json_string(monkeypatch):
    main = _reload_main()

    def _not_init():
        raise ValueError("not init")

    monkeypatch.setattr(main.firebase_admin, "get_app", _not_init)
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", "not-valid-json")
    with pytest.raises(ValueError, match="invalid JSON"):
        main.initialize_firebase()


def test_initialize_firebase_from_credentials_file(monkeypatch, tmp_path):
    main = _reload_main()

    def _not_init():
        raise ValueError("not init")

    monkeypatch.setattr(main.firebase_admin, "get_app", _not_init)
    creds_file = tmp_path / "creds.json"
    creds_file.write_text('{"type": "service_account"}')
    monkeypatch.setenv("FIREBASE_CREDENTIALS", str(creds_file))
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    init = MagicMock()
    cert = MagicMock(return_value="cred")
    monkeypatch.setattr(main.firebase_admin, "initialize_app", init)
    monkeypatch.setattr(main.credentials, "Certificate", cert)
    main.initialize_firebase()
    cert.assert_called_once_with(str(creds_file))
    init.assert_called_once_with("cred")


def test_development_static_uploads_mount(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path))
    sys.modules.pop("src.api.main", None)
    m = importlib.import_module("src.api.main")
    _patch_lifespan_side_effects(m)
    with TestClient(m.app):
        pass
```

- [ ] **Step 2: Run the test file — expect some failures related to `initialize_scheduled_notification_service`**

```bash
.venv/bin/python -m pytest tests/unit/api/test_api_main_firebase_and_lifespan.py -v
```

Expected: Failures because `main.py` still imports and calls `initialize_scheduled_notification_service`.

- [ ] **Step 3: Remove scheduler singletons from `base_dependencies.py`**

In `src/api/base_dependencies.py`, remove the entire block from line 307 to the end of `initialize_scheduled_notification_service()` and `get_daily_context_precompute_service()`. Also remove the import of `ScheduledNotificationService` at line 34–36.

The section to remove (starting at `# Scheduled Notification Service (singleton pattern...)`):

```python
# DELETE these lines from base_dependencies.py:

from src.infra.services.scheduled_notification_service import (   # line 34
    ScheduledNotificationService,                                   # line 35
)                                                                   # line 36

# ... and further down:

# Scheduled Notification Service (singleton pattern - create once and reuse)
_scheduled_notification_service = None


def get_scheduled_notification_service() -> ScheduledNotificationService:
    """
    Get the scheduled notification service instance (singleton).
    This is created during application startup in the lifespan function.

    Returns:
        ScheduledNotificationService: The scheduled notification service
    """
    return _scheduled_notification_service


def initialize_scheduled_notification_service() -> ScheduledNotificationService:
    """
    Initialize the scheduled notification service during application startup.

    Returns:
        ScheduledNotificationService: The initialized scheduled notification service
    """
    global _scheduled_notification_service
    if _scheduled_notification_service is None:
        from src.infra.services.scheduled_subscription_push_service import (
            ScheduledSubscriptionPushService,
        )

        firebase_service = get_firebase_service()
        trial_push_service = ScheduledSubscriptionPushService()
        _scheduled_notification_service = ScheduledNotificationService(
            firebase_service,
            _redis_client,
            trial_push_service=trial_push_service,
        )
        # Expose for webhook handler to purge stale trial rows on RENEWAL.
        _scheduled_notification_service.trial_push_service = trial_push_service
    return _scheduled_notification_service


def get_daily_context_precompute_service():
    """Get daily context precompute service for notification rescheduling."""
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    if _redis_client is None:
        return None
    return DailyContextPrecomputeService(_redis_client)
```

- [ ] **Step 4: Update `main.py` lifespan — remove scheduler and email startup**

Replace the lifespan function in `src/api/main.py` with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting MealTrack API...")

    # Initialize Firebase Admin SDK
    try:
        initialize_firebase()
    except Exception as e:
        logger.error("Failed to initialize Firebase: %s", e)
        raise

    # Warm database connection — triggers Neon compute wakeup on cold start
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        logger.info("Database connection warmed successfully")
    except Exception as e:
        logger.warning("Database connection warming failed: %s", e)

    # Initialize Redis cache
    try:
        await initialize_cache_layer()
    except Exception as exc:
        logger.error("Failed to initialize cache layer: %s", exc)
        if os.getenv("FAIL_ON_CACHE_ERROR", "false").lower() == "true":
            raise

    logger.info("MealTrack API started successfully!")
    yield

    # Shutdown
    logger.info("Shutting down MealTrack API...")
    await shutdown_cache_layer()

    if async_engine is not None:
        await async_engine.dispose()
```

- [ ] **Step 5: Clean up `main.py` imports**

Remove these import lines from `src/api/main.py`:

```python
# REMOVE these lines:
    initialize_scheduled_notification_service,        # from base_dependencies import block
from src.infra.services.scheduled_email_service import ScheduledEmailService
from src.infra.services.email_template_renderer import EmailTemplateRenderer
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.domain.services.email_service import EmailService
```

The updated `src/api/base_dependencies` import block in `main.py` becomes:

```python
from src.api.base_dependencies import (
    initialize_cache_layer,
    shutdown_cache_layer,
)
```

- [ ] **Step 6: Run the lifespan tests — all should pass**

```bash
.venv/bin/python -m pytest tests/unit/api/test_api_main_firebase_and_lifespan.py -v
```

Expected: All tests pass. `test_lifespan_scheduled_start_failure_still_starts_api` is gone.

- [ ] **Step 7: Run the full test suite to catch regressions**

```bash
.venv/bin/python -m pytest tests/unit/ -q --no-header
```

Expected: Same pass count as baseline (1336 passed, 3 skipped) minus any tests that directly tested the removed scheduler. Fix any unexpected failures before continuing.

- [ ] **Step 8: Commit**

```bash
git add src/api/main.py src/api/base_dependencies.py \
        tests/unit/api/test_api_main_firebase_and_lifespan.py
git commit -m "refactor: remove in-process notification scheduler from web service"
```

---

## Task 3: Create push notification cron

**Files:**
- Create: `src/cron/push.py`
- Create: `tests/unit/cron/test_push_cron.py`

- [ ] **Step 1: Write failing tests first**

Create `tests/unit/cron/test_push_cron.py`:

```python
"""Unit tests for the push notification cron entry point."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_push_cron_happy_path_runs_all_three_phases():
    """All three phases execute when DB is reachable."""
    with (
        patch("src.cron.push.initialize_sentry"),
        patch("src.cron.push.engine") as mock_engine,
        patch("src.cron.push.FirebaseService") as mock_firebase_cls,
        patch("src.cron.push.RedisClient") as mock_redis_cls,
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.ScheduledSubscriptionPushService") as mock_trial_cls,
        patch("src.cron.push.ScheduledNotificationService") as mock_svc_cls,
        patch("src.cron.push.UnitOfWork") as mock_uow_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up succeeds
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # UoW returns timezone rows
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = [
            MagicMock(timezone="Asia/Ho_Chi_Minh"),
            MagicMock(timezone="UTC"),
        ]
        mock_uow_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(session=mock_session))
        mock_uow_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Precompute service
        mock_precompute = AsyncMock()
        mock_precompute.precompute_for_timezone = AsyncMock()
        mock_precompute_cls.return_value = mock_precompute

        # Trial push service
        mock_trial = MagicMock()
        mock_trial.check_and_schedule_pushes = MagicMock()
        mock_trial_cls.return_value = mock_trial

        # FCM dispatch service
        mock_svc = MagicMock()
        mock_svc._send_due_notifications = AsyncMock()
        mock_svc_cls.return_value = mock_svc

        # Redis
        mock_redis = AsyncMock()
        mock_redis_cls.return_value = mock_redis

        from src.cron.push import run
        await run()

        # All three phases were invoked
        assert mock_precompute.precompute_for_timezone.call_count == 2  # one per timezone
        mock_trial.check_and_schedule_pushes.assert_called_once()
        mock_svc._send_due_notifications.assert_called_once()
        mock_redis.connect.assert_called_once()
        mock_redis.disconnect.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_push_cron_aborts_on_db_warmup_failure():
    """Early exit when DB warm-up fails — no phases run."""
    with (
        patch("src.cron.push.initialize_sentry"),
        patch("src.cron.push.engine") as mock_engine,
        patch("src.cron.push.RedisClient") as mock_redis_cls,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.ScheduledSubscriptionPushService") as mock_trial_cls,
        patch("src.cron.push.ScheduledNotificationService") as mock_svc_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up raises
        mock_engine.connect.side_effect = Exception("Neon cold start")

        from src.cron.push import run
        await run()  # should not raise

        mock_redis_cls.assert_not_called()
        mock_precompute_cls.assert_not_called()
        mock_trial_cls.assert_not_called()
        mock_svc_cls.assert_not_called()


@pytest.mark.asyncio
async def test_push_cron_phase_failure_does_not_abort_subsequent_phases():
    """A failure in Phase 1 does not prevent Phase 2 or Phase 3 from running."""
    with (
        patch("src.cron.push.initialize_sentry"),
        patch("src.cron.push.engine") as mock_engine,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.RedisClient") as mock_redis_cls,
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.ScheduledSubscriptionPushService") as mock_trial_cls,
        patch("src.cron.push.ScheduledNotificationService") as mock_svc_cls,
        patch("src.cron.push.UnitOfWork") as mock_uow_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up succeeds
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # Phase 1 raises
        mock_uow_cls.return_value.__enter__ = MagicMock(side_effect=RuntimeError("db error"))
        mock_uow_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Phase 2 and 3 services
        mock_trial = MagicMock()
        mock_trial.check_and_schedule_pushes = MagicMock()
        mock_trial_cls.return_value = mock_trial

        mock_svc = MagicMock()
        mock_svc._send_due_notifications = AsyncMock()
        mock_svc_cls.return_value = mock_svc

        mock_redis = AsyncMock()
        mock_redis_cls.return_value = mock_redis

        from src.cron.push import run
        await run()  # must not raise

        mock_trial.check_and_schedule_pushes.assert_called_once()
        mock_svc._send_due_notifications.assert_called_once()
```

- [ ] **Step 2: Run tests — expect ImportError (module doesn't exist yet)**

```bash
.venv/bin/python -m pytest tests/unit/cron/test_push_cron.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.cron.push'`

- [ ] **Step 3: Create `src/cron/push.py`**

```python
"""
Push notification cron entry point.

Run manually:  python -m src.cron.push
Render cron schedule:  */2 * * * *

Phases (all idempotent — safe to run concurrently):
  1. Precompute — insert NotificationORM rows for every user/timezone today
  2. Trial push — insert T-2d / T-1d trial-expiry rows
  3. Dispatch   — claim pending rows, send via FCM, mark sent
"""
import asyncio
import logging

import sentry_sdk
from sqlalchemy import text
from zoneinfo import ZoneInfo

from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.redis_client import RedisClient
from src.infra.config.settings import settings
from src.infra.database.config import engine
from src.infra.database.uow import UnitOfWork
from src.infra.monitoring.sentry import initialize_sentry
from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
from src.infra.services.firebase_service import FirebaseService
from src.infra.services.scheduled_notification_service import ScheduledNotificationService
from src.infra.services.scheduled_subscription_push_service import ScheduledSubscriptionPushService

logger = logging.getLogger(__name__)


async def run() -> None:
    """Execute all three notification phases then exit."""
    logging.basicConfig(level=logging.INFO)
    initialize_sentry()

    # DB warm-up — triggers Neon compute wakeup; abort if unreachable
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB warm-up failed (Neon cold start?): %s", exc)
        sentry_sdk.flush(timeout=5)
        return

    redis = RedisClient(redis_url=settings.redis_url, max_connections=2)
    await redis.connect()
    firebase = FirebaseService()  # initialises firebase_admin internally
    now = utc_now()

    # Phase 1 — precompute notification rows for each timezone today
    # DailyContextPrecomputeService.precompute_for_timezone() is idempotent:
    # it checks a Redis sentinel before doing DB work, so re-running is free.
    try:
        with UnitOfWork() as uow:
            tz_rows = uow.session.execute(
                text("SELECT DISTINCT timezone FROM users WHERE timezone IS NOT NULL")
            ).fetchall()
        timezones = [r.timezone for r in tz_rows]
        precompute = DailyContextPrecomputeService(redis)
        for tz_name in timezones:
            local_today = now.astimezone(ZoneInfo(tz_name)).date()
            await precompute.precompute_for_timezone(tz_name, local_today)
    except Exception:
        logger.exception("Phase 1 (precompute) failed")

    # Phase 2 — create trial-expiry push rows (T-2d / T-1d)
    # UNIQUE CONSTRAINT on (user_id, notification_type, scheduled_date) prevents duplicates.
    try:
        trial_push = ScheduledSubscriptionPushService()
        await asyncio.to_thread(trial_push.check_and_schedule_pushes, now)
    except Exception:
        logger.exception("Phase 2 (trial push scheduling) failed")

    # Phase 3 — claim due rows, render messages, batch FCM send, mark sent
    # status='processing' claim prevents double-sends on concurrent runs.
    try:
        svc = ScheduledNotificationService(firebase, redis, trial_push_service=None)
        await svc._send_due_notifications(now)
    except Exception:
        logger.exception("Phase 3 (FCM dispatch) failed")

    await redis.disconnect()
    engine.dispose()
    sentry_sdk.flush(timeout=5)


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 4: Run tests — all should pass**

```bash
.venv/bin/python -m pytest tests/unit/cron/test_push_cron.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/cron/push.py tests/unit/cron/test_push_cron.py
git commit -m "feat: add push notification cron entry point (src/cron/push.py)"
```

---

## Task 4: Create email notification cron

**Files:**
- Create: `src/cron/email.py`
- Create: `tests/unit/cron/test_email_cron.py`

- [ ] **Step 1: Write failing tests first**

Create `tests/unit/cron/test_email_cron.py`:

```python
"""Unit tests for the email notification cron entry point."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_email_cron_calls_check_and_send():
    """Happy path: DB reachable, emails are sent."""
    with (
        patch("src.cron.email.initialize_sentry"),
        patch("src.cron.email.engine") as mock_engine,
        patch("src.cron.email.async_engine", None),
        patch("src.cron.email.ResendEmailAdapter"),
        patch("src.cron.email.EmailTemplateRenderer"),
        patch("src.cron.email.EmailService"),
        patch("src.cron.email.ScheduledEmailService") as mock_ses_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up succeeds
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_ses = AsyncMock()
        mock_ses.check_and_send_emails = AsyncMock()
        mock_ses_cls.return_value = mock_ses

        from src.cron.email import run
        await run()

        mock_ses.check_and_send_emails.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_email_cron_aborts_on_db_warmup_failure():
    """Early exit when DB warm-up fails — no emails sent."""
    with (
        patch("src.cron.email.initialize_sentry"),
        patch("src.cron.email.engine") as mock_engine,
        patch("src.cron.email.ScheduledEmailService") as mock_ses_cls,
        patch("sentry_sdk.flush"),
    ):
        mock_engine.connect.side_effect = Exception("DB down")

        from src.cron.email import run
        await run()  # must not raise

        mock_ses_cls.assert_not_called()


@pytest.mark.asyncio
async def test_email_cron_logs_error_on_send_failure():
    """Email send failure is caught and logged; cron exits cleanly."""
    with (
        patch("src.cron.email.initialize_sentry"),
        patch("src.cron.email.engine") as mock_engine,
        patch("src.cron.email.async_engine", None),
        patch("src.cron.email.ResendEmailAdapter"),
        patch("src.cron.email.EmailTemplateRenderer"),
        patch("src.cron.email.EmailService"),
        patch("src.cron.email.ScheduledEmailService") as mock_ses_cls,
        patch("sentry_sdk.flush"),
    ):
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_ses = AsyncMock()
        mock_ses.check_and_send_emails = AsyncMock(side_effect=RuntimeError("Resend down"))
        mock_ses_cls.return_value = mock_ses

        from src.cron.email import run
        await run()  # must not raise

        mock_engine.dispose.assert_called_once()
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
.venv/bin/python -m pytest tests/unit/cron/test_email_cron.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.cron.email'`

- [ ] **Step 3: Create `src/cron/email.py`**

```python
"""
Email notification cron entry point.

Run manually:  python -m src.cron.email
Render cron schedule:  0 9 * * *  (09:00 UTC = 16:00 ICT / Vietnam)

Sends:
  - Re-engagement emails to trial users inactive 3+ days
  - Trial-expiring emails to users whose trial ends in 2 days
  Dedup: 7-day window prevents re-sending (email_log table).
"""
import asyncio
import logging

import sentry_sdk
from sqlalchemy import text

from src.domain.services.email_service import EmailService
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.infra.database.config import engine
from src.infra.database.config_async import async_engine
from src.infra.monitoring.sentry import initialize_sentry
from src.infra.services.email_template_renderer import EmailTemplateRenderer
from src.infra.services.scheduled_email_service import ScheduledEmailService

logger = logging.getLogger(__name__)


async def run() -> None:
    """Check for and send all scheduled lifecycle emails, then exit."""
    logging.basicConfig(level=logging.INFO)
    initialize_sentry()

    # DB warm-up — triggers Neon compute wakeup; abort if unreachable
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB warm-up failed: %s", exc)
        sentry_sdk.flush(timeout=5)
        return

    try:
        email_adapter = ResendEmailAdapter()
        email_renderer = EmailTemplateRenderer()
        email_service = EmailService(
            email_adapter=email_adapter, template_renderer=email_renderer
        )
        scheduled_email = ScheduledEmailService(email_service=email_service)
        await scheduled_email.check_and_send_emails()
    except Exception:
        logger.exception("Email cron failed")

    engine.dispose()
    if async_engine is not None:
        await async_engine.dispose()
    sentry_sdk.flush(timeout=5)


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 4: Run tests — all should pass**

```bash
.venv/bin/python -m pytest tests/unit/cron/test_email_cron.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/cron/email.py tests/unit/cron/test_email_cron.py
git commit -m "feat: add email notification cron entry point (src/cron/email.py)"
```

---

## Task 5: Create render.yaml

**Files:**
- Create: `render.yaml`

No unit tests — this is infrastructure config. Validate by inspecting the Render dashboard after deploy.

- [ ] **Step 1: Create `render.yaml` at the repo root**

```yaml
# Render Infrastructure as Code
# Docs: https://render.com/docs/infrastructure-as-code
#
# To apply: push this file to main. Render detects it automatically.
# Env var groups referenced here must exist in the Render dashboard first.

services:
  # ── Web service ────────────────────────────────────────────────────────────
  - type: web
    name: mealtrack-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT --workers 4
    envVars:
      - key: DATABASE_URL
        sync: false          # set in Render dashboard
      - key: REDIS_URL
        sync: false
      - key: FIREBASE_SERVICE_ACCOUNT_JSON
        sync: false
      - key: RESEND_API_KEY
        sync: false
      - key: SENTRY_DSN
        sync: false
      - key: ENVIRONMENT
        value: production
      - key: CACHE_ENABLED
        value: "true"

  # ── Push notification cron  (every 2 minutes) ──────────────────────────────
  - type: cron
    name: mealtrack-cron-push
    runtime: python
    schedule: "*/2 * * * *"
    buildCommand: pip install -r requirements.txt
    startCommand: python -m src.cron.push
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
      - key: FIREBASE_SERVICE_ACCOUNT_JSON
        sync: false
      - key: SENTRY_DSN
        sync: false
      - key: ENVIRONMENT
        value: production

  # ── Email lifecycle cron  (daily at 09:00 UTC = 16:00 ICT) ────────────────
  - type: cron
    name: mealtrack-cron-email
    runtime: python
    schedule: "0 9 * * *"
    buildCommand: pip install -r requirements.txt
    startCommand: python -m src.cron.email
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: RESEND_API_KEY
        sync: false
      - key: SENTRY_DSN
        sync: false
      - key: ENVIRONMENT
        value: production
```

- [ ] **Step 2: Commit**

```bash
git add render.yaml
git commit -m "feat: add render.yaml with web + push cron + email cron services"
```

---

## Task 6: Final validation

- [ ] **Step 1: Run the full unit test suite**

```bash
.venv/bin/python -m pytest tests/unit/ -q --no-header
```

Expected: At least 1336 passed (same baseline), 0 unexpected failures. New cron tests add to this count.

- [ ] **Step 2: Verify the web app still starts cleanly**

```bash
ENVIRONMENT=test .venv/bin/python -c "
from fastapi.testclient import TestClient
import sys, importlib
sys.modules.pop('src.api.main', None)
from unittest.mock import patch, MagicMock, AsyncMock

async def _noop(): pass

with patch('src.api.main.initialize_firebase'), \
     patch('src.api.main.initialize_cache_layer', _noop), \
     patch('src.api.main.shutdown_cache_layer', _noop), \
     patch('src.api.main.engine') as e:
    e.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
    e.connect.return_value.__exit__ = MagicMock(return_value=False)
    import src.api.main as m
    with TestClient(m.app) as c:
        r = c.get('/health')
        print('Status:', r.status_code)
        assert r.status_code == 200, r.text
print('Web service starts OK')
"
```

Expected: `Web service starts OK`

- [ ] **Step 3: Smoke-test push cron locally (dry run)**

```bash
ENVIRONMENT=test \
DATABASE_URL="<your-dev-db-url>" \
REDIS_URL="<your-dev-redis-url>" \
FIREBASE_SERVICE_ACCOUNT_JSON='<your-json>' \
.venv/bin/python -m src.cron.push
```

Expected: Logs show Phase 1, Phase 2, Phase 3 completing (or being skipped with sentinel hits). No unhandled exceptions.

- [ ] **Step 4: Smoke-test email cron locally (dry run)**

```bash
ENVIRONMENT=test \
DATABASE_URL="<your-dev-db-url>" \
RESEND_API_KEY="<your-key>" \
.venv/bin/python -m src.cron.email
```

Expected: Logs show email check running. With `EMAIL_ENABLED=false` (default), emails will be skipped at the Resend adapter level.

- [ ] **Step 5: Open PR**

```bash
git push origin worktree-feature+render-cron-notifications
gh pr create \
  --base feature/scheduled-email-feature-flag \
  --title "feat: move notification scheduling to Render cron services" \
  --body "$(cat <<'EOF'
## Summary
- Removes in-process `ScheduledNotificationService` loop from FastAPI lifespan (eliminates 80% CPU spikes)
- Removes one-shot `ScheduledEmailService` call from app startup
- Adds `src/cron/push.py`: push cron (*/2 * * * *) — precompute + trial rows + FCM dispatch
- Adds `src/cron/email.py`: email cron (0 9 * * *) — re-engagement + trial-expiring emails
- Adds `render.yaml`: defines web + 2 cron services as infrastructure as code

## Test plan
- [ ] All unit tests pass (`pytest tests/unit/`)
- [ ] Push cron smoke test passes locally
- [ ] Email cron smoke test passes locally
- [ ] Render dashboard shows 3 services after merging to main
- [ ] Monitor CPU on web service after deploy — should stay below 30%

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Quick Reference

| Command | Purpose |
|---|---|
| `python -m src.cron.push` | Run push cron manually |
| `python -m src.cron.email` | Run email cron manually |
| `pytest tests/unit/cron/ -v` | Run cron unit tests |
| `pytest tests/unit/ -q` | Full unit suite |
