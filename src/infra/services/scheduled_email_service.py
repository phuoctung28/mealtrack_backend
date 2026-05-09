"""Scheduled email service for re-engagement and trial expiring emails."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_

from src.domain.services.email_service import EmailService
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.email_log import EmailLog
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


class ScheduledEmailService:
    """Checks for and sends scheduled lifecycle emails."""

    INACTIVITY_THRESHOLD_DAYS = 3
    TRIAL_EXPIRING_DAYS = 2
    DUPLICATE_WINDOW_DAYS = 7

    def __init__(self, email_service: EmailService):
        self._email_service = email_service

    async def check_and_send_emails(self) -> None:
        """Main entry point — check and send all scheduled emails."""
        now = utc_now()
        logger.info("Running scheduled email check")

        # 1. Re-engagement emails (inactive trial users)
        inactive_users = await self._find_inactive_trial_users(now)
        for user in inactive_users:
            if await self._has_recent_email(user.id, "reengagement"):
                continue
            await self._send_reengagement(user)

        # 2. Trial expiring emails
        expiring = await self._find_expiring_trials(now)
        for user, days_left in expiring:
            if await self._has_recent_email(user.id, "trial_expiring"):
                continue
            await self._send_trial_expiring(user, days_left)

        logger.info(
            f"Scheduled email check complete: "
            f"{len(inactive_users)} inactive, {len(expiring)} expiring"
        )

    async def _find_inactive_trial_users(self, now: datetime) -> list:
        """Find trial users inactive for 3+ days."""
        threshold = now - timedelta(days=self.INACTIVITY_THRESHOLD_DAYS)
        trial_window = now - timedelta(days=7)

        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(User)
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        User.is_active == True,
                        User.email_opt_out == False,
                        User.last_accessed < threshold,
                        Subscription.status == "active",
                        Subscription.purchased_at > trial_window,
                    )
                )
            )
            return list(result.scalars().all())

    async def _find_expiring_trials(self, now: datetime) -> list[tuple]:
        """Find trials expiring in 2 days."""
        expiring_before = now + timedelta(days=self.TRIAL_EXPIRING_DAYS)
        expiring_after = now + timedelta(days=self.TRIAL_EXPIRING_DAYS - 1)

        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(User, Subscription)
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        User.is_active == True,
                        User.email_opt_out == False,
                        Subscription.status == "active",
                        Subscription.expires_at >= expiring_after,
                        Subscription.expires_at < expiring_before,
                    )
                )
            )
            rows = result.all()
            return [(row.User, self.TRIAL_EXPIRING_DAYS) for row in rows]

    async def _has_recent_email(self, user_id: str, email_type: str) -> bool:
        """Check if user received this email type within duplicate window."""
        cutoff = utc_now() - timedelta(days=self.DUPLICATE_WINDOW_DAYS)

        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(EmailLog).where(
                    and_(
                        EmailLog.user_id == user_id,
                        EmailLog.email_type == email_type,
                        EmailLog.sent_at > cutoff,
                    )
                )
            )
            return result.scalars().first() is not None

    async def _send_reengagement(self, user) -> None:
        """Send re-engagement email and log it."""
        result = await self._email_service.send_reengagement_email(
            user, days_inactive=self.INACTIVITY_THRESHOLD_DAYS, streak_days=0
        )

        if result.success:
            await self._log_email(user.id, "reengagement", result.message_id)
            logger.info(f"Re-engagement email sent to user {user.id}")

    async def _send_trial_expiring(self, user, days_left: int) -> None:
        """Send trial expiring email and log it."""
        result = await self._email_service.send_trial_expiring_email(
            user, days_left=days_left, meals_logged=0, streak_days=0
        )

        if result.success:
            await self._log_email(user.id, "trial_expiring", result.message_id)
            logger.info(f"Trial expiring email sent to user {user.id}")

    async def _log_email(self, user_id: str, email_type: str, message_id: str | None) -> None:
        """Log sent email to database."""
        async with AsyncUnitOfWork() as uow:
            email_log = EmailLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                email_type=email_type,
                sent_at=utc_now(),
                resend_message_id=message_id,
                status="sent",
            )
            uow.session.add(email_log)
