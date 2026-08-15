from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.nutrition_integrity_policy import (
    NUTRITION_INTEGRITY_POLICY_VERSION,
)
from src.infra.repositories.food_reference_integrity_repository import (
    UnsupportedIntegrityPolicyError,
)


@pytest.mark.asyncio
async def test_control_repository_fails_closed_when_runtime_does_not_support_db_policy():
    from src.infra.repositories.food_reference_integrity_repository import (
        FoodReferenceIntegrityRepository,
    )

    row = MagicMock(
        active_policy_version="nutrition_integrity_v2",
        catalog_integrity_generation=4,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    repository = FoodReferenceIntegrityRepository(session)

    with pytest.raises(UnsupportedIntegrityPolicyError):
        await repository.get_active_control()


@pytest.mark.asyncio
async def test_control_repository_returns_supported_policy_and_generation():
    from src.infra.repositories.food_reference_integrity_repository import (
        FoodReferenceIntegrityRepository,
    )

    row = MagicMock(
        active_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        catalog_integrity_generation=4,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    control = await FoodReferenceIntegrityRepository(session).get_active_control()

    assert control.active_policy_version == NUTRITION_INTEGRITY_POLICY_VERSION
    assert control.catalog_integrity_generation == 4
