"""Claim-owned atomic profile restoration; it never calls committing CQRS handlers."""

import hashlib
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.web_funnel_claim_common import (
    claim_conflict,
    claim_not_found,
    utcnow,
)
from src.app.services.web_funnel_claim_exchange import reservation_is_bound
from src.domain.model.auth import AuthProvider
from src.domain.model.user import Goal, JobType, Sex, TdeeRequest, TrainingLevel
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User
from src.infra.database.models.web_funnel_claim import (
    WebFunnelClaim,
    WebFunnelLead,
)
from src.infra.database.models.weekly.weekly_macro_budget import WeeklyMacroBudgetORM


def _age(snapshot: dict) -> int:
    born = date(snapshot["birth_year"], snapshot["birth_month"], snapshot["birth_day"])
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _result(snapshot: dict, revenuecat_customer_id: str) -> dict:
    age = _age(snapshot)
    request = TdeeRequest(
        age=age,
        sex=Sex(snapshot["gender"]),
        height=snapshot["height"],
        weight=snapshot["weight"],
        body_fat_pct=snapshot.get("body_fat_percentage"),
        job_type=JobType(snapshot["job_type"]),
        training_days_per_week=snapshot["training_days_per_week"],
        training_minutes_per_session=snapshot["training_minutes_per_session"],
        goal=Goal(snapshot["goal"]),
        training_level=TrainingLevel(snapshot["training_level"])
        if snapshot.get("training_level")
        else None,
    )
    calculation = TdeeCalculationService().calculate_tdee(request)
    macros = calculation.macros
    if all(
        snapshot.get(key) is not None
        for key in ("custom_protein_g", "custom_carbs_g", "custom_fat_g")
    ):
        protein, carbs, fat = (
            float(snapshot[key])
            for key in ("custom_protein_g", "custom_carbs_g", "custom_fat_g")
        )
        macro_data = {
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "calories": protein * 4 + carbs * 4 + fat * 9,
        }
    else:
        macro_data = {
            "protein": macros.protein,
            "carbs": macros.carbs,
            "fat": macros.fat,
            "calories": macros.calories,
        }
    return {
        "version": "claim_result_v1",
        "onboarding_completed": True,
        "age": age,
        "tdee": calculation.tdee,
        "macros": macro_data,
        "access_status": "pending",
        "revenuecat_customer_id": revenuecat_customer_id,
    }


def _username(email: str) -> str:
    return f"wf_{hashlib.sha256(email.encode()).hexdigest()[:24]}"


def _week_start(today: date) -> date:
    return date.fromordinal(today.toordinal() - today.weekday())


async def complete_claim(
    db: AsyncSession, uid: str, email: str | None, exchange_token: str
) -> dict:
    """Create all local effects under the request's one transaction and commit once."""
    claim = await db.scalar(
        select(WebFunnelClaim)
        .where(
            WebFunnelClaim.exchange_token_hash
            == hashlib.sha256(exchange_token.encode()).hexdigest()
        )
        .with_for_update()
    )
    if not claim:
        raise claim_not_found()
    lead = await db.get(WebFunnelLead, claim.lead_id, with_for_update=True)
    if (
        not lead
        or lead.status in {"refunded", "revoked", "conflict"}
        or claim.revoked_at
        or claim.expires_at <= utcnow()
    ):
        raise claim_not_found()
    if claim.consumed_at:
        if claim.consumed_uid == uid:
            return claim.result or {
                "version": "claim_result_v1",
                "access_status": lead.access_sync_status,
            }
        raise claim_conflict()
    if (
        not reservation_is_bound(claim, uid, exchange_token)
        or (email or "").lower() != lead.email.lower()
    ):
        raise claim_conflict()
    user = await db.scalar(
        select(User).where(User.firebase_uid == uid).with_for_update()
    )
    email_owner = await db.scalar(
        select(User).where(User.email == lead.email).with_for_update()
    )
    if email_owner and email_owner.firebase_uid != uid:
        raise claim_conflict()
    if not user:
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
    elif user.email != lead.email:
        raise claim_conflict()
    user.onboarding_completed = True
    user.revenuecat_customer_id = lead.id
    profile = await db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user.id, UserProfile.is_current.is_(True))
        .with_for_update()
    )
    snapshot = lead.snapshot
    if profile is None:
        profile = UserProfile(
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
        db.add(profile)
    else:
        profile.age = _age(snapshot)
        profile.gender = snapshot["gender"]
        profile.height_cm = snapshot["height"]
        profile.weight_kg = snapshot["weight"]
        profile.body_fat_percentage = snapshot.get("body_fat_percentage")
        profile.date_of_birth = date(
            snapshot["birth_year"], snapshot["birth_month"], snapshot["birth_day"]
        )
        profile.job_type = snapshot["job_type"]
        profile.training_days_per_week = snapshot["training_days_per_week"]
        profile.training_minutes_per_session = snapshot["training_minutes_per_session"]
        profile.fitness_goal = snapshot["goal"]
    result = _result(lead.snapshot, lead.id)
    current_week = _week_start(date.today())
    budget = await db.scalar(
        select(WeeklyMacroBudgetORM)
        .where(
            WeeklyMacroBudgetORM.user_id == user.id,
            WeeklyMacroBudgetORM.week_start_date == current_week,
        )
        .with_for_update()
    )
    if budget is None:
        macros = result["macros"]
        db.add(
            WeeklyMacroBudgetORM(
                weekly_budget_id=str(uuid.uuid4()),
                user_id=user.id,
                week_start_date=current_week,
                target_calories=macros["calories"] * 7,
                target_protein=macros["protein"] * 7,
                target_carbs=macros["carbs"] * 7,
                target_fat=macros["fat"] * 7,
            )
        )
    claim.consumed_uid, claim.consumed_at, claim.result = uid, utcnow(), result
    lead.claimed_at, lead.claimed_uid, lead.status = utcnow(), uid, "claimed"
    await db.commit()
    return result


async def recover_claim(
    db: AsyncSession, uid: str, reservation_id: str | None, generation: int | None
) -> dict:
    """Return only the caller's completed result or a safe completion-required state."""
    claim = await db.scalar(
        select(WebFunnelClaim)
        .where(WebFunnelClaim.reservation_uid == uid)
        .order_by(WebFunnelClaim.created_at.desc())
    )
    if not claim:
        raise claim_not_found()
    if claim.consumed_uid == uid:
        return claim.result or {
            "version": "claim_result_v1",
            "access_status": "pending",
        }
    if (
        reservation_id == claim.reservation_id
        and generation == claim.generation
        and reservation_is_bound(claim, uid, None)
    ):
        return {"version": "claim_result_v1", "status": "completion_required"}
    raise claim_not_found()
