"""Browser-safe responses for the public web-funnel draft API."""

from datetime import datetime

from pydantic import BaseModel


class WebFunnelLeadCreatedResponse(BaseModel):
    """Safe projection returned after a browser creates a draft."""

    lead_id: str
    masked_email: str
    state: str


class WebFunnelLeadStatusResponse(BaseModel):
    """Safe draft status; it deliberately excludes payment and credential data."""

    lead_id: str
    masked_email: str
    state: str
    resend_available_at: datetime | None = None
    retry_after_seconds: int = 0


class WebFunnelClaimResultResponse(BaseModel):
    """Versioned result for an authenticated, completed email-link claim."""

    schema_version: str = "claim_result_v1"
    claim_status: str
    access_sync_status: str
    retry_after_seconds: int | None = None
    plan_snapshot: dict | None = None


class WebFunnelClaimRecoveryResponse(BaseModel):
    """Non-secret cold-start recovery state for the signed-in user only."""

    status: str
    retry_after_seconds: int | None = None
    plan_ready: bool = False
