"""Unit tests for identity-specific persistence behavior."""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from src.domain.exceptions.firebase_identity_exceptions import (
    FirebaseIdentityConflictError,
)
from src.domain.model.auth.auth_provider import AuthProvider
from src.domain.model.user import UserDomainModel
from src.infra.repositories.user_repository_async import AsyncUserRepository


class _NoRowResult:
    def scalars(self):
        return self

    def first(self):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize("constraint", ["users_email_key", "users_firebase_uid_key"])
async def test_save_translates_identity_unique_constraint_to_conflict(
    constraint: str,
) -> None:
    session = Mock()
    session.execute = AsyncMock(return_value=_NoRowResult())
    session.flush = AsyncMock(
        side_effect=IntegrityError(
            "INSERT", {}, Exception(f'duplicate key value violates unique constraint "{constraint}"')
        )
    )
    repository = AsyncUserRepository(session)
    user = UserDomainModel(
        id=None,
        firebase_uid="firebase-uid",
        email="buyer@example.com",
        username="buyer",
        password_hash="",
        provider=AuthProvider.GOOGLE,
    )

    with pytest.raises(FirebaseIdentityConflictError):
        await repository.save(user)
