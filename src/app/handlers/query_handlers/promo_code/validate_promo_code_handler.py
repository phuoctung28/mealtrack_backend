"""Query handler — validate a promo code: existence, active status, usage cap, already-redeemed."""
import logging

from src.app.queries.promo_code.validate_promo_code_query import (
    PromoCodeValidationError,
    ValidatePromoCodeQuery,
)
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


class ValidatePromoCodeQueryHandler:
    async def handle(self, query: ValidatePromoCodeQuery) -> dict:
        async with AsyncUnitOfWork() as uow:
            repo = uow.promo_codes

            promo = await repo.get_by_code(query.code)
            if not promo:
                raise PromoCodeValidationError(status_code=404, detail="Promo code not found")

            if not promo.is_active:
                raise PromoCodeValidationError(
                    status_code=422, detail="This promo code is no longer available"
                )

            if promo.expires_at is not None and promo.expires_at < utc_now():
                raise PromoCodeValidationError(
                    status_code=422, detail="This promo code has expired"
                )

            if promo.current_uses >= promo.max_uses:
                raise PromoCodeValidationError(
                    status_code=422, detail="This promo code is no longer available"
                )

            existing = await repo.get_redemption(
                promo_code_id=promo.id, user_id=query.user_id
            )
            if existing:
                raise PromoCodeValidationError(
                    status_code=422, detail="You've already used this code"
                )

            if (
                promo.source_offering_id is not None
                and query.current_offering_id != promo.source_offering_id
            ):
                raise PromoCodeValidationError(
                    status_code=422, detail="Code is not valid for this offering"
                )

            return {
                "code": promo.code,
                "rc_offering_id": promo.rc_offering_id,
                "is_valid": True,
            }
