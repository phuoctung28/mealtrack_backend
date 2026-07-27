"""Request schemas for web funnel checkout APIs."""

from pydantic import BaseModel, ConfigDict, Field


class WebFunnelCheckoutRequest(BaseModel):
    """Create or reuse a backend-owned checkout."""

    model_config = ConfigDict(populate_by_name=True)

    lead_id: str = Field(alias="leadId", min_length=1, max_length=128)
    offer_id: str = Field(alias="offerId", min_length=1, max_length=64)
    reward_id: str = Field(alias="rewardId", min_length=1, max_length=64)
    billing_country: str = Field(alias="billingCountry", min_length=2, max_length=2)
    idempotency_key: str = Field(alias="idempotencyKey", min_length=8, max_length=128)


class PayPalConfirmationRequest(BaseModel):
    """Bind a PayPal SDK subscription reference to a checkout."""

    model_config = ConfigDict(populate_by_name=True)

    subscription_id: str = Field(alias="subscriptionId", min_length=3, max_length=255)


class WebFunnelClaimRequest(BaseModel):
    """Claim a paid checkout into the authenticated app user."""

    model_config = ConfigDict(populate_by_name=True)

    claim_token: str = Field(alias="claimToken", min_length=16, max_length=255)
