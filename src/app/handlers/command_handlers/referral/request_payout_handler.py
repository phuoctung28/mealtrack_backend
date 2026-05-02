"""Command handler — validate wallet balance and create a referral payout request."""
import logging

from src.app.commands.referral.request_payout_command import RequestPayoutCommand
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.repositories.referral_repository import ReferralRepository

logger = logging.getLogger(__name__)

MIN_WITHDRAWAL = 100_000  # ₫100,000


class RequestPayoutCommandHandler:
    async def handle(self, command: RequestPayoutCommand) -> None:
        async with AsyncUnitOfWork() as uow:
            repo = ReferralRepository(uow.session)

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

            logger.info(
                "Payout request created: user=%s amount=%d method=%s",
                command.user_id,
                command.amount,
                command.payment_method,
            )
