import logging
import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Optional

from fastapi import FastAPI, Request

from src.infra.database.config import SessionLocal
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.models.meal.meal import Meal as DBMeal
from src.infra.database.models.meal.meal_image import MealImage as DBMealImage
from src.infra.database.models.nutrition.nutrition import Nutrition as DBNutrition
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User

logger = logging.getLogger(__name__)


def _ensure_dev_user() -> Optional[User]:
    """Create or fetch the single development user and profile.

    This is safe to call multiple times. Returns the persisted SQLAlchemy User instance
    loaded from a short-lived session; do not store it for reuse across requests.

    Returns None if database isn't ready (e.g., during test collection).
    """
    firebase_uid = os.getenv("DEV_USER_FIREBASE_UID", "dev_firebase_uid")
    email = os.getenv("DEV_USER_EMAIL", "dev@example.com")
    username = os.getenv("DEV_USER_USERNAME", "dev_user")

    session = SessionLocal()
    try:
        user: Optional[User] = (
            session.query(User).filter(User.firebase_uid == firebase_uid).first()
        )

        if user:
            return user

        # Create new dev user
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            username=username,
            first_name="Dev",
            last_name="User",
            password_hash="dev_password_placeholder",
            is_active=True,
            onboarding_completed=True,
        )
        session.add(user)
        session.flush()

        # Create a basic current profile
        profile = UserProfile(
            user_id=user.id,
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            body_fat_percentage=18.0,
            is_current=True,
            activity_level="moderate",
            fitness_goal="maintenance",
            target_weight_kg=70.0,
            meals_per_day=3,
            snacks_per_day=1,
            dietary_preferences=[],
            health_conditions=[],
            allergies=[],
            pain_points=[],
        )
        session.add(profile)
        session.commit()

        logger.info("Created development user '%s' (%s)", username, user.id)
        return user
    except Exception as exc:
        session.rollback()
        logger.warning("Failed to ensure dev user (database may not be ready): %s", exc)
        return None
    finally:
        session.close()


def add_dev_auth_bypass(app: FastAPI) -> None:
    """Install a dev-only middleware that sets request.state.user.

    The injected user has an `id` attribute and an `is_premium()` method that returns True
    so premium-only endpoints work in development.
    """
    if os.getenv("ENVIRONMENT") != "development":
        logger.info("Dev auth bypass not enabled (ENVIRONMENT != development)")
        return

    # Try to ensure the user exists up-front and seed meals (may fail during test collection)
    user = _ensure_dev_user()
    if user:
        _seed_dev_meals(user.id)
    else:
        logger.warning("Dev user creation deferred - will create on first request")

    @app.middleware("http")
    async def dev_user_injector(request: Request, call_next):  # type: ignore[override]
        # Load fresh per request to avoid cross-session ORM usage
        session = SessionLocal()
        try:
            firebase_uid = os.getenv("DEV_USER_FIREBASE_UID", "dev_firebase_uid")
            user: Optional[User] = (
                session.query(User).filter(User.firebase_uid == firebase_uid).first()
            )

            if user is None:
                user = _ensure_dev_user()

            # Provide only what downstream code expects
            request.state.user = SimpleNamespace(
                id=user.id,
                firebase_uid=user.firebase_uid,
                email=user.email,
                username=user.username,
                is_premium=lambda: True,
            )
        finally:
            session.close()

        return await call_next(request)


def _seed_dev_meals(user_id: str) -> None:
    """Seed a small set of meals with nutrition for today's date if none exist.
    Creates breakfast, lunch, dinner with simple nutrition totals so daily macros works.
    """
    session = SessionLocal()
    try:
        # Check if there are any meals today for this user
        from datetime import date, timedelta
        today = date.today()
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)

        existing = (
            session.query(DBMeal)
            .filter(DBMeal.user_id == user_id)
            .filter(DBMeal.created_at >= start_dt)
            .filter(DBMeal.created_at < end_dt)
            .count()
        )
        if existing > 0:
            # Backfill missing ready_at for READY meals created earlier without it
            meals_missing_ready = (
                session.query(DBMeal)
                .filter(DBMeal.user_id == user_id)
                .filter(DBMeal.created_at >= start_dt)
                .filter(DBMeal.created_at < end_dt)
                .filter(DBMeal.status == MealStatusEnum.READY)
                .filter(DBMeal.ready_at.is_(None))
                .all()
            )
            if meals_missing_ready:
                now = datetime.now(timezone.utc)
                for m in meals_missing_ready:
                    m.ready_at = m.created_at or now
                    m.updated_at = now
                session.commit()
            return

        def create_meal(meal_name: str, calories: float, p: float, c: float, f: float):
            meal_id = str(uuid.uuid4())
            image_id = str(uuid.uuid4())
            # Minimal image row (FK is required)
            db_image = DBMealImage(
                image_id=image_id,
                format="jpeg",
                size_bytes=12345,
                width=800,
                height=600,
                url=None,
            )
            session.add(db_image)

            now = datetime.now(timezone.utc)
            db_meal = DBMeal(
                meal_id=meal_id,
                user_id=user_id,
                status=MealStatusEnum.READY,
                dish_name=meal_name,
                image_id=image_id,
                created_at=now,
                updated_at=now,
                ready_at=now,
            )
            session.add(db_meal)

            db_nutrition = DBNutrition(
                calories=calories,
                protein=p,
                carbs=c,
                fat=f,
                confidence_score=0.95,
                meal_id=meal_id,
            )
            session.add(db_nutrition)

        # Seed three meals
        create_meal("Breakfast Oatmeal", 420.0, 20.0, 60.0, 10.0)
        create_meal("Chicken Salad Lunch", 650.0, 50.0, 30.0, 30.0)
        create_meal("Salmon Dinner", 700.0, 45.0, 40.0, 35.0)

        session.commit()
        logger.info("Seeded dev meals for user %s", user_id)
    except Exception as exc:
        session.rollback()
        logger.error("Failed to seed dev meals: %s", exc)
    finally:
        session.close()


