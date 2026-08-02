"""High-value claim endpoints require a recently minted Firebase bearer."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from src.api.routes.v1.web_funnel import _require_fresh_token
from src.app.services.web_funnel_claim_common import utcnow


def test_fresh_claim_bearer_is_accepted():
    _require_fresh_token({"iat": int(utcnow().timestamp())})


@pytest.mark.parametrize(
    "issued_at",
    [
        int((utcnow() - timedelta(minutes=11)).timestamp()),
        int((utcnow() + timedelta(minutes=1)).timestamp()),
    ],
)
def test_stale_or_future_claim_bearer_is_rejected(issued_at):
    with pytest.raises(HTTPException) as error:
        _require_fresh_token({"iat": issued_at})
    assert error.value.status_code == 401
