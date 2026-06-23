"""Promo code API routes — validate before purchase, redeem after purchase."""
import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src.api.dependencies.auth import get_current_user_id
from src.app.commands.promo_code.redeem_promo_code_command import RedeemPromoCodeCommand
from src.app.handlers.command_handlers.promo_code.redeem_promo_code_handler import (
    RedeemPromoCodeCommandHandler,
)
from src.app.handlers.query_handlers.promo_code.validate_promo_code_handler import (
    ValidatePromoCodeQueryHandler,
)
from src.app.queries.promo_code.validate_promo_code_query import (
    PromoCodeValidationError,
    ValidatePromoCodeQuery,
)

router = APIRouter(prefix="/v1/promo-codes", tags=["Promo Codes"])
logger = logging.getLogger(__name__)


class PromoCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    current_offering_id: Optional[str] = Field(None, max_length=50)

    @field_validator("code")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        return v.strip().upper()


class ValidatePromoCodeResponse(BaseModel):
    code: str
    rc_offering_id: str
    is_valid: bool


@router.post("/validate", response_model=ValidatePromoCodeResponse)
async def validate_promo_code(
    request: PromoCodeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Validate a promo code before purchase. Does not increment usage."""
    try:
        handler = ValidatePromoCodeQueryHandler()
        result = await handler.handle(
            ValidatePromoCodeQuery(
                code=request.code,
                user_id=user_id,
                current_offering_id=request.current_offering_id,
            )
        )
        return ValidatePromoCodeResponse(**result)
    except PromoCodeValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/redeem", status_code=status.HTTP_200_OK)
async def redeem_promo_code(
    request: PromoCodeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Record a promo code redemption after successful RC purchase. Increments usage."""
    try:
        handler = RedeemPromoCodeCommandHandler()
        await handler.handle(
            RedeemPromoCodeCommand(code=request.code, user_id=user_id)
        )
        return {"success": True}
    except PromoCodeValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
