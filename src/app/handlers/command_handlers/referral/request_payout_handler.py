"""Command handler — validate wallet balance and create a referral payout request."""

import logging
from typing import Optional

from src.app.commands.referral.request_payout_command import RequestPayoutCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.referral_repository_async import AsyncReferralRepository

logger = logging.getLogger(__name__)

MIN_WITHDRAWAL = 100_000  # ₫100,000


@handles(RequestPayoutCommand)
class RequestPayoutCommandHandler(EventHandler[RequestPayoutCommand, None]):
    def __init__(self, uow: Optional[AsyncUnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, command: RequestPayoutCommand) -> None:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            repo = AsyncReferralRepository(uow.session)

            pending = await repo.get_pending_payout(command.user_id)
            if pending:
                raise ValueError("pending_payout_exists")

            wallet = await repo.get_or_create_wallet(command.user_id)
            if wallet.balance < MIN_WITHDRAWAL:
                raise ValueError(f"minimum_withdrawal_{MIN_WITHDRAWAL}")

            if command.amount > wallet.balance:
                raise ValueError("insufficient_balance")

            if command.amount < MIN_WITHDRAWAL:
                raise ValueError(f"minimum_withdrawal_{MIN_WITHDRAWAL}")

            await repo.create_payout_request(
                user_id=command.user_id,
                amount=command.amount,
                method=command.payment_method,
                details=command.payment_details,
            )

            wallet.balance -= command.amount
            wallet.total_withdrawn += command.amount
            wallet.updated_at = utc_now()

            logger.info(
                "Payout request created: user=%s amount=%d method=%s",
                command.user_id,
                command.amount,
                command.payment_method,
            )
