"""Request schemas for the public web-funnel draft API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateWebFunnelLeadRequest(BaseModel):
    """Bounded, non-payment data collected before a web checkout starts."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=254)
    source: Literal["nutree_web_funnel"] = "nutree_web_funnel"
    source_revision: str = Field(default="v1", min_length=1, max_length=32)


class CompleteWebFunnelClaimRequest(BaseModel):
    """Opaque email-link capability; all claimant identity comes from Firebase."""

    model_config = ConfigDict(extra="forbid")

    claim_token: str = Field(..., min_length=1, max_length=512)
