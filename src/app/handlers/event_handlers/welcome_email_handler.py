"""Welcome email handler — sends welcome email on user onboarding."""

import logging
import uuid

from src.app.events.base import EventHandler, handles
from src.app.events.user.user_onboarded_event import UserOnboardedEvent
from src.domain.services.email_service import EmailService
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.email_log import EmailLog
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(UserOnboardedEvent)
class WelcomeEmailHandler(EventHandler[UserOnboardedEvent, None]):
    """Sends welcome email when user completes onboarding."""

    def __init__(self, email_service: EmailService):
        self._email_service = email_service

    async def handle(self, event: UserOnboardedEvent) -> None:
        async with AsyncUnitOfWork() as uow:
            user = await uow.users.find_by_id(event.user_id)

            if not user:
                logger.warning(f"User not found for welcome email: {event.user_id}")
                return

            # Skip if already sent or opted out
            if user.welcome_email_sent_at:
                logger.debug(f"Welcome email already sent to user {user.id}")
                return

            if user.email_opt_out:
                logger.debug(f"User {user.id} opted out of emails")
                return

            # Send welcome email
            result = await self._email_service.send_welcome_email(
                user, tdee=int(event.tdee)
            )

            if result.success:
                # Mark as sent
                user.welcome_email_sent_at = utc_now()

                # Log the email
                email_log = EmailLog(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    email_type="welcome",
                    sent_at=utc_now(),
                    resend_message_id=result.message_id,
                    status="sent",
                )
                uow.session.add(email_log)
                await uow.commit()

                logger.info(f"Welcome email sent to user {user.id}")
            else:
                logger.error(f"Failed to send welcome email to {user.id}: {result.error}")
