import json
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def _lead_params(suffix: str) -> dict[str, object]:
    lead_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    return {
        "id": lead_id,
        "created_at": now,
        "updated_at": now,
        "email": f"repeat-{suffix}@example.com",
        "access_key_hash": uuid.uuid4().hex,
        "request_id": f"repeat-purchase-{suffix}-{uuid.uuid4().hex}",
        "snapshot_version": "web_onboarding_snapshot_v1",
        "snapshot": json.dumps({"target_calories": 2000}),
        "snapshot_hash": uuid.uuid4().hex,
        "status": "claimed",
        "revision": 1,
        "claimed_uid": "firebase-repeat-user",
        "access_sync_status": "active",
    }


async def _insert_lead(session, params: dict[str, object]) -> None:
    await session.execute(
        text(
            """
            INSERT INTO web_funnel_leads (
                id, created_at, updated_at, email, access_key_hash, request_id,
                snapshot_version, snapshot, snapshot_hash, status, revision,
                claimed_uid, access_sync_status
            ) VALUES (
                :id, :created_at, :updated_at, :email, :access_key_hash, :request_id,
                :snapshot_version, CAST(:snapshot AS JSON), :snapshot_hash, :status,
                :revision, :claimed_uid, :access_sync_status
            )
            """
        ),
        params,
    )


async def _insert_redemption(
    session,
    *,
    lead_id: str,
    suffix: str,
    redemption_link_hash: str,
    finalization_key_hash: str,
) -> None:
    now = datetime.now(UTC)
    await session.execute(
        text(
            """
            INSERT INTO web_funnel_redemptions (
                id, created_at, updated_at, lead_id, provider, environment, project,
                original_app_user_id, verified_app_user_id, entitlement_id, product_id,
                verified_at, finalized_uid, redeemer_uid, redemption_link_hash,
                finalization_key_hash, result
            ) VALUES (
                :id, :created_at, :updated_at, :lead_id, 'revenuecat', 'SANDBOX',
                'default', :original_app_user_id, :verified_app_user_id, 'standard',
                'web_monthly', :verified_at, 'firebase-repeat-user',
                'firebase-repeat-user', :redemption_link_hash, :finalization_key_hash,
                CAST(:result AS JSON)
            )
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "created_at": now,
            "updated_at": now,
            "lead_id": lead_id,
            "original_app_user_id": f"$RCAnonymousID:repeat-{suffix}",
            "verified_app_user_id": f"$RCAnonymousID:repeat-{suffix}",
            "verified_at": now,
            "redemption_link_hash": redemption_link_hash,
            "finalization_key_hash": finalization_key_hash,
            "result": json.dumps({"access_status": "active"}),
        },
    )


@pytest.mark.asyncio
async def test_postgres_allows_repeat_uid_but_preserves_purchase_uniqueness(pg_session):
    first_lead = _lead_params("first")
    second_lead = _lead_params("second")
    first_link_hash = uuid.uuid4().hex * 2
    first_finalization_key_hash = uuid.uuid4().hex * 2
    await _insert_lead(pg_session, first_lead)
    await _insert_lead(pg_session, second_lead)
    await _insert_redemption(
        pg_session,
        lead_id=first_lead["id"],
        suffix="first",
        redemption_link_hash=first_link_hash,
        finalization_key_hash=first_finalization_key_hash,
    )
    await _insert_redemption(
        pg_session,
        lead_id=second_lead["id"],
        suffix="second",
        redemption_link_hash=uuid.uuid4().hex * 2,
        finalization_key_hash=uuid.uuid4().hex * 2,
    )

    duplicate_link_lead = _lead_params("duplicate-link")
    duplicate_customer_lead = _lead_params("duplicate-customer")
    duplicate_key_lead = _lead_params("duplicate-key")
    duplicate_lead_id_lead = _lead_params("duplicate-lead-id")
    for lead in (
        duplicate_link_lead,
        duplicate_customer_lead,
        duplicate_key_lead,
        duplicate_lead_id_lead,
    ):
        await _insert_lead(pg_session, lead)
    try:
        with pytest.raises(IntegrityError):
            async with pg_session.begin_nested():
                await _insert_redemption(
                    pg_session,
                    lead_id=duplicate_link_lead["id"],
                    suffix="duplicate-link",
                    redemption_link_hash=first_link_hash,
                    finalization_key_hash=uuid.uuid4().hex * 2,
                )
        with pytest.raises(IntegrityError):
            async with pg_session.begin_nested():
                await _insert_redemption(
                    pg_session,
                    lead_id=duplicate_customer_lead["id"],
                    suffix="first",
                    redemption_link_hash=uuid.uuid4().hex * 2,
                    finalization_key_hash=uuid.uuid4().hex * 2,
                )
        with pytest.raises(IntegrityError):
            async with pg_session.begin_nested():
                await _insert_redemption(
                    pg_session,
                    lead_id=duplicate_key_lead["id"],
                    suffix="duplicate-key",
                    redemption_link_hash=uuid.uuid4().hex * 2,
                    finalization_key_hash=first_finalization_key_hash,
                )
        with pytest.raises(IntegrityError):
            async with pg_session.begin_nested():
                await _insert_redemption(
                    pg_session,
                    lead_id=first_lead["id"],
                    suffix="duplicate-lead-id",
                    redemption_link_hash=uuid.uuid4().hex * 2,
                    finalization_key_hash=uuid.uuid4().hex * 2,
                )
    finally:
        await pg_session.rollback()
