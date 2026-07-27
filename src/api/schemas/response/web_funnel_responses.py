"""Response schemas for web funnel checkout APIs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckoutResponse(BaseModel):
    """Frontend PayPal checkout contract."""

    model_config = ConfigDict(populate_by_name=True)

    checkout_id: str = Field(alias="checkoutId")
    status: str
    provider: str
    plan_id: str | None = Field(alias="planId")
    custom_id: str = Field(alias="customId")
    offer_id: str = Field(alias="offerId")
    reward_id: str = Field(alias="rewardId")
    currency: str
    amount_minor: int = Field(alias="amountMinor")
    standard_amount_minor: int = Field(alias="standardAmountMinor")
    renewal_amount_minor: int = Field(alias="renewalAmountMinor")
    renewal_description: str = Field(alias="renewalDescription")
    renewal_interval: str = Field(alias="renewalInterval")
    welcome_discount_percent: int = Field(alias="welcomeDiscountPercent")


class CheckoutStatusResponse(BaseModel):
    """Safe checkout status for browser polling."""

    model_config = ConfigDict(populate_by_name=True)

    checkout_id: str = Field(alias="checkoutId")
    status: str
    provider: str
    claimable: bool
    claimed: bool
    paid_at: datetime | None = Field(alias="paidAt")
    claim_token: str | None = Field(default=None, alias="claimToken")


class WebFunnelClaimResponse(BaseModel):
    """Claim result for an authenticated user."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    subscription_id: str = Field(alias="subscriptionId")
