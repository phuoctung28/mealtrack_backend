"""Atomic onboarding restoration after a provider-verified RevenueCat redemption."""

import hashlib
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def utcnow():
    from datetime import UTC, datetime
    return datetime.now(UTC)


def claim_conflict():
    return HTTPException(status_code=409, detail="Claim conflict")


def claim_not_found():
    return HTTPException(status_code=404, detail="Claim not found")


def _age(snapshot):
    return snapshot.get("age", 30)


def _username(email):
    return email.split("@", 1)[0][:50]


def _week_start(today):
    return today.fromordinal(today.toordinal() - today.weekday())


def _result(snapshot, uid):
    return {
        "firebase_uid": uid,
        "onboarding_completed": True,
        "macros": {
            "calories": snapshot.get("target_calories", 2000),
            "protein": snapshot.get("custom_protein_g", 150),
            "carbs": snapshot.get("custom_carbs_g", 200),
            "fat": snapshot.get("custom_fat_g", 65),
        },
    }
from src.domain.model.auth import AuthProvider
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel_claim import (
    WebFunnelLead,
    WebFunnelRedemption,
)
from src.infra.database.models.weekly.weekly_macro_budget import WeeklyMacroBudgetORM


async def finalize_redemption(
    db: AsyncSession,
    *,
    uid: str,
    email: str,
    original_app_user_id: str,
    idempotency_key: str,
    environment: str,
    project: str,
) -> dict:
    """Restore one paid lead once; the provider-derived original ID selects the lead."""
    binding = await db.scalar(
        select(WebFunnelRedemption)
        .where(
            WebFunnelRedemption.original_app_user_id == original_app_user_id,
            WebFunnelRedemption.environment == environment,
            WebFunnelRedemption.project == project,
        )
        .with_for_update()
    )
    if not binding:
        raise claim_not_found()
    # Redemptions correlated before this rollout have no opaque preflight token.
    # They retain the prior finalization path; all newly issued tokens require
    # the Firebase UID bound by preflight before the link can be finalized.
    if binding.preflight_token_hash and binding.preflight_uid != uid:
        raise claim_not_found()
    if binding.redeemer_uid != uid:
        raise claim_not_found()
    key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
    if binding.finalized_uid:
        if binding.finalized_uid != uid or binding.finalization_key_hash != key_hash:
            raise claim_conflict()
        return binding.result or {
            "version": "redemption_result_v1",
            "access_status": "active",
        }
    lead = await db.get(WebFunnelLead, binding.lead_id, with_for_update=True)
    if not lead or lead.status in {"refunded", "revoked", "conflict"}:
        raise claim_not_found()
    if email.lower() != lead.email.lower():
        raise claim_conflict()
    user = await db.scalar(
        select(User).where(User.firebase_uid == uid).with_for_update()
    )
    email_owner = await db.scalar(
        select(User).where(User.email == lead.email).with_for_update()
    )
    if email_owner and email_owner.firebase_uid != uid:
        raise claim_conflict()
    if user and (user.email.lower() != lead.email.lower() or user.onboarding_completed):
        raise claim_conflict()
    if user is None:
        user = User(
            firebase_uid=uid,
            email=lead.email,
            username=_username(lead.email),
            password_hash="",
            provider=AuthProvider.EMAIL_LINK,
            onboarding_completed=True,
        )
        db.add(user)
        await db.flush()
    user.onboarding_completed = True
    user.revenuecat_customer_id = uid
    snapshot = lead.snapshot
    profile = await db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user.id, UserProfile.is_current.is_(True))
        .with_for_update()
    )
    if profile is not None:
        raise claim_conflict()
    db.add(
        UserProfile(
            user_id=user.id,
            age=_age(snapshot),
            gender=snapshot["gender"],
            height_cm=snapshot["height"],
            weight_kg=snapshot["weight"],
            body_fat_percentage=snapshot.get("body_fat_percentage"),
            date_of_birth=date(
                snapshot["birth_year"], snapshot["birth_month"], snapshot["birth_day"]
            ),
            job_type=snapshot["job_type"],
            training_days_per_week=snapshot["training_days_per_week"],
            training_minutes_per_session=snapshot["training_minutes_per_session"],
            fitness_goal=snapshot["goal"],
            meals_per_day=snapshot.get("meals_per_day", 3),
            pain_points=snapshot.get("pain_points", []),
            dietary_preferences=snapshot.get("dietary_preferences", []),
            training_level=snapshot.get("training_level"),
            challenge_duration=snapshot.get("challenge_duration"),
            training_types=snapshot.get("training_types"),
            custom_protein_g=snapshot.get("custom_protein_g"),
            custom_carbs_g=snapshot.get("custom_carbs_g"),
            custom_fat_g=snapshot.get("custom_fat_g"),
            target_weight_kg=snapshot.get("target_weight_kg"),
        )
    )
    result = {
        **_result(snapshot, uid),
        "version": "redemption_result_v1",
        "access_status": "active",
    }
    week_start = _week_start(date.today())
    budget = await db.scalar(
        select(WeeklyMacroBudgetORM)
        .where(
            WeeklyMacroBudgetORM.user_id == user.id,
            WeeklyMacroBudgetORM.week_start_date == week_start,
        )
        .with_for_update()
    )
    if budget is None:
        macros = result["macros"]
        db.add(
            WeeklyMacroBudgetORM(
                weekly_budget_id=str(uuid.uuid4()),
                user_id=user.id,
                week_start_date=week_start,
                target_calories=macros["calories"] * 7,
                target_protein=macros["protein"] * 7,
                target_carbs=macros["carbs"] * 7,
                target_fat=macros["fat"] * 7,
            )
        )
    db.add(
        Subscription(
            user_id=user.id,
            revenuecat_subscriber_id=uid,
            product_id=binding.product_id,
            platform="ios",
            status="active",
            purchased_at=utcnow(),
            is_sandbox=binding.environment.upper() == "SANDBOX",
        )
    )
    binding.finalized_uid, binding.finalized_at = uid, utcnow()
    binding.finalization_key_hash, binding.result = key_hash, result
    lead.claimed_uid, lead.claimed_at, lead.status, lead.access_sync_status = (
        uid,
        utcnow(),
        "claimed",
        "active",
    )
    await db.commit()
    return result
