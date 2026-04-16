"""Infra implementation of NotificationDedupPort using SQLAlchemy."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from src.domain.ports.notification_dedup_port import NotificationDedupPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config import ScopedSession
from src.infra.database.models.notification.notification_sent_log import (
    NotificationSentLog,
)

logger = logging.getLogger(__name__)


class NotificationSentLogDedupStore(NotificationDedupPort):
    def try_claim_sent(self, *, user_id: str, notification_type: str, minute_key: str) -> bool:
        db = ScopedSession()
        try:
            db.add(
                NotificationSentLog(
                    user_id=user_id,
                    notification_type=notification_type,
                    sent_minute=minute_key,
                )
            )
            db.commit()
            return False  # We claimed it — proceed to send
        except IntegrityError:
            db.rollback()
            return True  # Another worker already claimed it
        except Exception as e:  # noqa: BLE001
            db.rollback()
            logger.warning("Dedup claim failed, allowing send: %s", e)
            return False  # Fail-open: send rather than silently drop
        finally:
            db.close()

    def cleanup_old_sent_logs(self, *, older_than_hours: int) -> int:
        cutoff = utc_now() - timedelta(hours=older_than_hours)
        db = ScopedSession()
        try:
            deleted = (
                db.query(NotificationSentLog)
                .filter(NotificationSentLog.sent_at < cutoff)
                .delete()
            )
            db.commit()
            return int(deleted or 0)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            logger.error("Error cleaning up sent logs: %s", e)
            return 0
        finally:
            db.close()

