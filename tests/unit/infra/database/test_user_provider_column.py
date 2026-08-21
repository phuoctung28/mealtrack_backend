from src.domain.model.auth.auth_provider import AuthProvider
from src.infra.database.models.user.user import (
    AUTH_PROVIDER_VARCHAR_LENGTH,
    User,
)


def test_provider_varchar_fits_all_auth_provider_names() -> None:
    longest_name = max(len(member.name) for member in AuthProvider)

    assert User.provider.type.length == AUTH_PROVIDER_VARCHAR_LENGTH
    assert AUTH_PROVIDER_VARCHAR_LENGTH >= longest_name
    assert AUTH_PROVIDER_VARCHAR_LENGTH >= len(AuthProvider.EMAIL_LINK.name)
