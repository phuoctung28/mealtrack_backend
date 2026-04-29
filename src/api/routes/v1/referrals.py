"""Referral system API routes — code lookup, validation, application, stats, and payout."""
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from src.api.dependencies.auth import get_current_user_id
from src.app.commands.referral.apply_referral_code_command import ApplyReferralCodeCommand
from src.app.commands.referral.request_payout_command import RequestPayoutCommand
from src.app.handlers.command_handlers.referral.apply_referral_code_handler import (
    ApplyReferralCodeCommandHandler,
)
from src.app.handlers.command_handlers.referral.request_payout_handler import (
    RequestPayoutCommandHandler,
)
from src.app.handlers.query_handlers.referral.get_my_referral_code_handler import (
    GetMyReferralCodeQueryHandler,
)
from src.app.handlers.query_handlers.referral.get_referral_stats_handler import (
    GetReferralStatsQueryHandler,
)
from src.app.handlers.query_handlers.referral.validate_referral_code_handler import (
    ValidateReferralCodeQueryHandler,
)
from src.app.queries.referral.get_my_referral_code_query import GetMyReferralCodeQuery
from src.app.queries.referral.get_referral_stats_query import GetReferralStatsQuery
from src.app.queries.referral.validate_referral_code_query import ValidateReferralCodeQuery

router = APIRouter(prefix="/v1/referrals", tags=["Referrals"])
logger = logging.getLogger(__name__)


# ── Request / Response Schemas ────────────────────────────────────────────────

class ValidateCodeRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        return v.strip().upper()


class ValidateCodeResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    referrer_name: Optional[str] = None
    discount_monthly: int = 199000
    discount_annual: int = 499000


class ApplyCodeRequest(BaseModel):
    code: str
    discount_applied: int

    @field_validator("code")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        return v.strip().upper()


class MyCodeResponse(BaseModel):
    code: str
    created_at: str


class ConversionDTO(BaseModel):
    referred_name: str
    status: str
    amount: int
    date: str


class StatsResponse(BaseModel):
    code: str
    wallet_balance: int
    total_earned: int
    total_withdrawn: int
    total_invited: int
    total_converted: int
    conversions: List[ConversionDTO]
    has_pending_payout: bool


class PayoutRequest(BaseModel):
    amount: int
    payment_method: str
    payment_details: Dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/validate", response_model=ValidateCodeResponse)
async def validate_code(
    request: ValidateCodeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Validate a referral code before the user completes their purchase."""
    handler = ValidateReferralCodeQueryHandler()
    result = await handler.handle(
        ValidateReferralCodeQuery(code=request.code, user_id=user_id),
    )
    return ValidateCodeResponse(**result.__dict__)


@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_code(
    request: ApplyCodeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Record the referred user's code application (call after purchase confirmation)."""
    try:
        handler = ApplyReferralCodeCommandHandler()
        await handler.handle(
            ApplyReferralCodeCommand(
                user_id=user_id,
                code=request.code,
                discount_applied=request.discount_applied,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True}


@router.get("/my-code", response_model=MyCodeResponse)
async def get_my_code(user_id: str = Depends(get_current_user_id)):
    """Return (or lazily create) the authenticated user's personal referral code."""
    handler = GetMyReferralCodeQueryHandler()
    result = await handler.handle(GetMyReferralCodeQuery(user_id=user_id))
    return MyCodeResponse(**result.__dict__)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user_id: str = Depends(get_current_user_id)):
    """Return wallet balance, lifetime totals, and per-conversion history."""
    handler = GetReferralStatsQueryHandler()
    result = await handler.handle(GetReferralStatsQuery(user_id=user_id))
    return StatsResponse(
        code=result.code,
        wallet_balance=result.wallet_balance,
        total_earned=result.total_earned,
        total_withdrawn=result.total_withdrawn,
        total_invited=result.total_invited,
        total_converted=result.total_converted,
        conversions=[ConversionDTO(**c.__dict__) for c in result.conversions],
        has_pending_payout=result.has_pending_payout,
    )


@router.post("/payout", status_code=status.HTTP_201_CREATED)
async def request_payout(
    request: PayoutRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Request a withdrawal of referral wallet balance (minimum ₫100,000)."""
    handler = RequestPayoutCommandHandler()
    try:
        await handler.handle(
            RequestPayoutCommand(
                user_id=user_id,
                amount=request.amount,
                payment_method=request.payment_method,
                payment_details=request.payment_details,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True}
