from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine, insert, select, update
from sqlalchemy.dialects import postgresql

from src.domain.services.nutrition_integrity_policy import (
    NUTRITION_INTEGRITY_POLICY_VERSION,
)
from src.infra.database.models.food_reference_model import FoodReferenceModel
from src.infra.database.models.nutrition_integrity import (
    FoodReferenceIntegrityControlModel,
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


def test_public_eligibility_waits_for_atomic_policy_activation():
    from src.infra.repositories.food_reference_integrity_repository import (
        FoodReferenceIntegrityRepository,
    )

    clause = FoodReferenceIntegrityRepository(MagicMock()).public_eligibility_clause()
    sql = str(
        clause.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "activation_run_id IS NULL" in sql
    assert "activation_run_id IS NOT NULL" in sql
    assert "integrity_status = 'valid'" in sql


def test_existing_verified_rows_remain_visible_until_activation_then_filter():
    from src.infra.repositories.food_reference_integrity_repository import (
        FoodReferenceIntegrityRepository,
    )

    engine = create_engine("sqlite:///:memory:")
    FoodReferenceModel.__table__.create(engine)
    FoodReferenceIntegrityControlModel.__table__.create(engine)
    clause = FoodReferenceIntegrityRepository(MagicMock()).public_eligibility_clause()

    with engine.begin() as connection:
        connection.execute(
            insert(FoodReferenceIntegrityControlModel),
            {
                "id": 1,
                "active_policy_version": NUTRITION_INTEGRITY_POLICY_VERSION,
                "catalog_integrity_generation": 0,
                "activation_run_id": None,
                "updated_at": datetime(2026, 8, 15),
            },
        )
        connection.execute(
            insert(FoodReferenceModel),
            [
                {
                    "id": 1,
                    "name": "Legacy Rice",
                    "is_verified": True,
                    "integrity_status": "unknown",
                    "integrity_policy_version": None,
                },
                {
                    "id": 2,
                    "name": "Materialized Rice",
                    "is_verified": True,
                    "integrity_status": "valid",
                    "integrity_policy_version": NUTRITION_INTEGRITY_POLICY_VERSION,
                },
            ],
        )

        pending_ids = (
            connection.execute(select(FoodReferenceModel.id).where(clause))
            .scalars()
            .all()
        )
        connection.execute(
            update(FoodReferenceIntegrityControlModel)
            .where(FoodReferenceIntegrityControlModel.id == 1)
            .values(activation_run_id="run-1")
        )
        activated_ids = (
            connection.execute(select(FoodReferenceModel.id).where(clause))
            .scalars()
            .all()
        )

    assert pending_ids == [1, 2]
    assert activated_ids == [2]


@pytest.mark.asyncio
async def test_activate_policy_accepts_a_fully_classified_quarantined_row():
    from src.infra.repositories.food_reference_integrity_repository import (
        FoodReferenceIntegrityRepository,
    )

    row = MagicMock(
        active_policy_version=NUTRITION_INTEGRITY_POLICY_VERSION,
        catalog_integrity_generation=4,
        activation_run_id=None,
        deployed_revision=None,
        updated_at=None,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.scalar = AsyncMock(return_value=0)
    session.flush = AsyncMock()

    control = await FoodReferenceIntegrityRepository(session).activate_policy(
        NUTRITION_INTEGRITY_POLICY_VERSION,
        activation_run_id="run-1",
        deployed_revision="revision-1",
    )

    incomplete_query = session.scalar.call_args.args[0]
    sql = str(
        incomplete_query.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "quarantined" in sql
    assert row.activation_run_id == "run-1"
    assert control.catalog_integrity_generation == 5
