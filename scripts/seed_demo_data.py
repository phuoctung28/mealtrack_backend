"""
Demo data seed script for app store screenshots.

Populates a demo user with 6 days of realistic nutrition data:
meals, food items, weekly budget, and cheat days.

Usage (run from backend worktree root):
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --reset
    python scripts/seed_demo_data.py --user-id <existing-user-id>

Prerequisites:
    .env with DATABASE_URL or DB_* vars (set DB_SSL_ENABLED=false for local dev)
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session

from src.infra.database.config import SessionLocal
from scripts.seed_demo_user import find_demo_user, reset_demo_data, seed_user
from scripts.seed_demo_db import seed_meals, seed_weekly_budget, seed_cheat_days

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run(reset: bool, target_user_id: str | None) -> None:
    """Execute the full seed workflow inside a single transaction."""
    db: Session = SessionLocal()
    try:
        if target_user_id:
            # Seed nutrition data onto an existing user — skip user creation
            user_id = target_user_id
            logger.info("Targeting existing user_id=%s", user_id)
        else:
            existing_id = find_demo_user(db)
            if existing_id:
                if not reset:
                    logger.warning(
                        "Demo user already exists (id=%s). Re-run with --reset to recreate.",
                        existing_id,
                    )
                    return
                logger.info("Resetting existing demo user id=%s", existing_id)
                reset_demo_data(db, existing_id)
            user_id = seed_user(db)
            logger.info("Created demo user (id=%s)", user_id)

        seed_meals(db, user_id)
        logger.info("Meals seeded.")

        seed_weekly_budget(db, user_id)
        logger.info("Weekly budget seeded.")

        seed_cheat_days(db, user_id)
        logger.info("Cheat days seeded.")

        db.commit()
        logger.info("Done. Demo user_id=%s", user_id)

    except Exception as exc:
        db.rollback()
        logger.error("Seed failed — rolled back. Reason: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed realistic demo data for app store screenshots."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing demo data before re-seeding.",
    )
    parser.add_argument(
        "--user-id",
        dest="user_id",
        default=None,
        help="Target an existing user by ID (skips demo user creation).",
    )
    args = parser.parse_args()
    run(reset=args.reset, target_user_id=args.user_id)


if __name__ == "__main__":
    main()
