"""Command handler — record a referred user's code application as a pending conversion."""

import logging

from src.app.commands.referral.apply_referral_code_command import (
    ApplyReferralCodeCommand,
)
from src.infra.repositories.referral_repository import ReferralRepository

logger = logging.getLogger(__name__)


class ApplyReferralCodeCommandHandler:
    def handle(self, command: ApplyReferralCodeCommand, uow) -> None:
        repo = ReferralRepository(uow.session)

        code = repo.get_code_by_code(command.code)
        if not code:
            raise ValueError("invalid_code")

        if code.user_id == command.user_id:
            raise ValueError("self_referral")

        existing = repo.get_conversion_by_referred_user(command.user_id)
        if existing:
            raise ValueError("already_referred")

        repo.create_conversion(
            referrer_user_id=code.user_id,
            referred_user_id=command.user_id,
            code=command.code,
            discount=command.discount_applied,
        )
        uow.commit()
        logger.info(
            "Referral conversion created: referrer=%s referred=%s",
            code.user_id,
            command.user_id,
        )
