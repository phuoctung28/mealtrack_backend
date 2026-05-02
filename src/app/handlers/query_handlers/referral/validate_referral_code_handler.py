"""Query handler — validate a referral code: existence, self-referral, already-referred checks."""

import logging

from sqlalchemy import select

from src.app.queries.referral.validate_referral_code_query import (
    ValidateCodeResult,
    ValidateReferralCodeQuery,
)
from src.infra.database.models.user.user import User
from src.infra.repositories.referral_repository import ReferralRepository

logger = logging.getLogger(__name__)


class ValidateReferralCodeQueryHandler:
    def handle(self, query: ValidateReferralCodeQuery, uow) -> ValidateCodeResult:
        repo = ReferralRepository(uow.session)

        code = repo.get_code_by_code(query.code)
        if not code:
            return ValidateCodeResult(valid=False, error="invalid_code")

        if code.user_id == query.user_id:
            return ValidateCodeResult(valid=False, error="self_referral")

        existing = repo.get_conversion_by_referred_user(query.user_id)
        if existing:
            return ValidateCodeResult(valid=False, error="already_referred")

        # Fetch referrer's first name for personalised UI copy
        result = uow.session.execute(
            select(User.first_name, User.display_name).where(User.id == code.user_id)
        )
        row = result.first()
        referrer_name = "Friend"
        if row:
            raw = row.first_name or row.display_name or ""
            referrer_name = raw.split()[0] if raw.strip() else "Friend"

        return ValidateCodeResult(
            valid=True,
            referrer_name=referrer_name,
            discount_monthly=199000,
            discount_annual=499000,
        )
