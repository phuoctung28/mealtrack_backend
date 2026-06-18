"""Query handler — unified code validation: tries promo_codes first, then referral_codes, then affiliate."""

import logging

from sqlalchemy import select

from src.app.queries.codes.validate_code_query import (
    CodeValidationError,
    ValidateCodeQuery,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.adapters.affiliate_service_adapter import AffiliateServiceAdapter
from src.infra.config.settings import settings
from src.infra.database.models.user.user import User
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


class ValidateCodeQueryHandler:
    async def handle(self, query: ValidateCodeQuery) -> dict:
        async with AsyncUnitOfWork() as uow:
            promo_repo = uow.promo_codes
            referral_repo = uow.referrals

            # ── Promo code lookup (wins on namespace collision) ──────────────
            promo = await promo_repo.get_by_code(query.code)
            if promo:
                if not promo.is_active:
                    raise CodeValidationError(422, "Code is no longer available")
                if promo.expires_at is not None and promo.expires_at < utc_now():
                    raise CodeValidationError(422, "This code has expired")
                if promo.current_uses >= promo.max_uses:
                    raise CodeValidationError(422, "Code is no longer available")
                existing = await promo_repo.get_redemption(
                    promo_code_id=promo.id, user_id=query.user_id
                )
                if existing:
                    raise CodeValidationError(422, "You have already used this code")
                return {
                    "type": "promo_code",
                    "code": promo.code,
                    "is_valid": True,
                    "rc_offering_id": promo.rc_offering_id,
                    "description": promo.description,
                }

            # ── Referral code lookup ─────────────────────────────────────────
            ref_code = await referral_repo.get_code_by_code(query.code)
            if ref_code:
                if ref_code.user_id == query.user_id:
                    raise CodeValidationError(
                        422, "You cannot use your own referral code"
                    )
                existing_conversion = (
                    await referral_repo.get_conversion_by_referred_user(query.user_id)
                )
                if existing_conversion:
                    raise CodeValidationError(422, "You have already used this code")

                result = await uow.session.execute(
                    select(User.first_name, User.display_name).where(
                        User.id == ref_code.user_id
                    )
                )
                row = result.first()
                referrer_name = "Friend"
                if row:
                    raw = row.first_name or row.display_name or ""
                    referrer_name = raw.split()[0] if raw.strip() else "Friend"

                return {
                    "type": "referral_code",
                    "code": ref_code.code,
                    "is_valid": True,
                    "referrer_name": referrer_name,
                    "discount_monthly": 199000,
                    "discount_annual": 499000,
                    "commission_rewards": settings.REFERRAL_COMMISSIONS,
                }

            # ── Affiliate code lookup (env-gated, last resort) ───────────────
            # nutree-affiliate owns duplicate-attribution enforcement; MealTrack
            # stores no attribution state.
            if settings.AFFILIATE_INTEGRATION_ENABLED:
                aff_result = await AffiliateServiceAdapter().validate_code(query.code)
                if aff_result.active:
                    return {
                        "type": "affiliate_code",
                        "code": query.code,
                        "is_valid": True,
                        "affiliate_id": aff_result.affiliate_id,
                        "display_name": aff_result.display_name,
                        "partner_type": aff_result.partner_type,
                    }

            raise CodeValidationError(404, "Code not found")
