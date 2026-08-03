"""Safe request contracts for RevenueCat web-customer correlation."""

import pytest
from pydantic import ValidationError

from src.api.schemas.request.web_funnel_claim_requests import (
    WebFunnelRevenueCatCorrelationRequest,
)


def test_correlation_request_accepts_revenuecat_anonymous_id():
    request = WebFunnelRevenueCatCorrelationRequest.model_validate(
        {"app_user_id": "$RCAnonymousID:87c6049c58069238dce29853916d624c"}
    )

    assert request.app_user_id.startswith("$RCAnonymousID:")


def test_correlation_request_rejects_extra_or_blank_values():
    with pytest.raises(ValidationError):
        WebFunnelRevenueCatCorrelationRequest.model_validate(
            {"app_user_id": "", "raw_redemption_url": "secret"}
        )
