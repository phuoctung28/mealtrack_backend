"""Unified code validation — accepts promo codes and referral codes via a single endpoint."""
import logging
from typing import Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.api.dependencies.auth import get_current_user_id
from src.app.handlers.query_handlers.codes.validate_code_handler import ValidateCodeQueryHandler
from src.app.queries.codes.validate_code_query import CodeValidationError, ValidateCodeQuery

router = APIRouter(prefix="/v1/codes", tags=["Codes"])
logger = logging.getLogger(__name__)


class CodeValidateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)

    @field_validator("code")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().upper()


class PromoValidatedResponse(BaseModel):
    type: Literal["promo_code"]
    code: str
    is_valid: bool
    rc_offering_id: Optional[str] = None
    description: Optional[str] = None


class ReferralValidatedResponse(BaseModel):
    type: Literal["referral_code"]
    code: str
    is_valid: bool
    referrer_name: str
    discount_monthly: int
    discount_annual: int


@router.post(
    "/validate",
    response_model=Union[PromoValidatedResponse, ReferralValidatedResponse],
)
async def validate_code(
    request: CodeValidateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Validate any code (promo or referral) before purchase. Does not redeem."""
    try:
        handler = ValidateCodeQueryHandler()
        result = await handler.handle(ValidateCodeQuery(code=request.code, user_id=user_id))
        return result
    except CodeValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
