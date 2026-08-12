"""Regression tests for the Firebase user-sync route."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.routes.v1.users import sync_user_from_firebase
from src.api.schemas.request.user_requests import UserSyncRequest
from src.domain.exceptions.firebase_identity_exceptions import (
    FirebaseIdentityConflictError,
)


@pytest.mark.asyncio
async def test_sync_maps_email_uid_collision_to_generic_conflict() -> None:
    event_bus = SimpleNamespace(
        send=AsyncMock(
            side_effect=FirebaseIdentityConflictError("internal identity detail")
        )
    )
    request = UserSyncRequest(
        firebase_uid="new-firebase-uid",
        email="buyer@example.com",
        provider="google",
    )
    http_request = SimpleNamespace(headers={"accept-language": "en-US,en"})

    with pytest.raises(HTTPException) as exc_info:
        await sync_user_from_firebase(
            request=request,
            http_request=http_request,
            token={"uid": "new-firebase-uid"},
            event_bus=event_bus,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Account identity could not be verified"
