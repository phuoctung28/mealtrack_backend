"""
Demo user and profile seeding/reset operations.

Owns: users, user_profiles tables for the demo account.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.meal.meal import Meal
from src.infra.database.models.weekly.weekly_macro_budget import WeeklyMacroBudget
from src.infra.database.models.cheat_day.cheat_day import CheatDay
from src.infra.database.models.enums import MealStatusEnum  # noqa: F401 — referenced by callers
from src.api.schemas.common.auth_enums import AuthProviderEnum

DEMO_FIREBASE_UID = "demo_firebase_uid_seed_v1"
DEMO_EMAIL = "demo@nutree.ai"
DEMO_USERNAME = "alex_demo"
DEMO_DISPLAY_NAME = "Alex Demo"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def find_demo_user(db: Session) -> str | None:
    """Return user_id of existing demo user, or None."""
    user = db.query(User).filter(User.firebase_uid == DEMO_FIREBASE_UID).first()
    return user.id if user else None


def reset_demo_data(db: Session, user_id: str) -> None:
    """Delete all demo data for user_id and commit."""
    for meal in db.query(Meal).filter(Meal.user_id == user_id).all():
        db.delete(meal)
    db.query(WeeklyMacroBudget).filter(WeeklyMacroBudget.user_id == user_id).delete()
    db.query(CheatDay).filter(CheatDay.user_id == user_id).delete()
    db.query(UserProfile).filter(UserProfile.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()


def seed_user(db: Session) -> str:
    """Insert demo User + UserProfile. Returns new user_id."""
    user_id = str(uuid.uuid4())

    db.add(User(
        id=user_id,
        firebase_uid=DEMO_FIREBASE_UID,
        email=DEMO_EMAIL,
        username=DEMO_USERNAME,
        display_name=DEMO_DISPLAY_NAME,
        first_name="Alex",
        last_name="Demo",
        password_hash="demo_hash_not_for_auth",
        provider=AuthProviderEnum.GOOGLE,
        is_active=True,
        onboarding_completed=True,
        last_accessed=_utc_now(),
        timezone="Asia/Ho_Chi_Minh",
    ))

    # Profile: 28yo male, 175cm, 70kg, desk job, 4 training days × 45 min, cut goal
    db.add(UserProfile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        age=28,
        gender="male",
        height_cm=175.0,
        weight_kg=70.0,
        is_current=True,
        job_type="desk",
        training_days_per_week=4,
        training_minutes_per_session=45,
        fitness_goal="cut",
        training_level="intermediate",
        target_weight_kg=67.0,
        meals_per_day=3,
        snacks_per_day=1,
        dietary_preferences=[],
        health_conditions=[],
        allergies=[],
    ))

    return user_id
