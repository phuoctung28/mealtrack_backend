"""Update fitness_goal columns to use new enum values (cut/bulk/recomp)

Revision ID: 012
Revises: 011
Create Date: 2026-01-05 10:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update fitness_goal columns to use new enum values.

    Changes:
    - user_profiles.fitness_goal: Update default from 'maintenance' to 'recomp'
    - meal_plans.fitness_goal: Convert to ENUM with cut/bulk/recomp
    - Migrate existing data: maintenance→recomp, cutting→cut, bulking→bulk
    """

    # Step 1: Update existing data in user_profiles
    logger.info("Migrating existing fitness_goal values in user_profiles...")
    op.execute("""
        UPDATE user_profiles
        SET fitness_goal = CASE
            WHEN fitness_goal = 'maintenance' THEN 'recomp'
            WHEN fitness_goal = 'cutting' THEN 'cut'
            WHEN fitness_goal = 'bulking' THEN 'bulk'
            WHEN fitness_goal = 'maintain' THEN 'recomp'
            WHEN fitness_goal = 'lose_weight' THEN 'cut'
            WHEN fitness_goal = 'weight_loss' THEN 'cut'
            WHEN fitness_goal = 'gain_weight' THEN 'bulk'
            WHEN fitness_goal = 'build_muscle' THEN 'bulk'
            WHEN fitness_goal = 'muscle_gain' THEN 'bulk'
            ELSE fitness_goal
        END
        WHERE fitness_goal IN ('maintenance', 'cutting', 'bulking', 'maintain',
                              'lose_weight', 'weight_loss', 'gain_weight',
                              'build_muscle', 'muscle_gain')
    """)

    # Step 2: Update default value for user_profiles.fitness_goal
    logger.info("Updating user_profiles.fitness_goal default value to 'recomp'...")
    op.alter_column(
        'user_profiles',
        'fitness_goal',
        existing_type=sa.String(length=30),
        server_default='recomp',
        nullable=False
    )

    # Step 3: Update existing data in meal_plans
    logger.info("Migrating existing fitness_goal values in meal_plans...")
    op.execute("""
        UPDATE meal_plans
        SET fitness_goal = CASE
            WHEN fitness_goal = 'maintenance' THEN 'recomp'
            WHEN fitness_goal = 'cutting' THEN 'cut'
            WHEN fitness_goal = 'bulking' THEN 'bulk'
            WHEN fitness_goal = 'maintain' THEN 'recomp'
            WHEN fitness_goal = 'lose_weight' THEN 'cut'
            WHEN fitness_goal = 'weight_loss' THEN 'cut'
            WHEN fitness_goal = 'gain_weight' THEN 'bulk'
            WHEN fitness_goal = 'build_muscle' THEN 'bulk'
            WHEN fitness_goal = 'muscle_gain' THEN 'bulk'
            ELSE fitness_goal
        END
        WHERE fitness_goal IN ('maintenance', 'cutting', 'bulking', 'maintain',
                              'lose_weight', 'weight_loss', 'gain_weight',
                              'build_muscle', 'muscle_gain')
    """)

    # Step 4: Convert meal_plans.fitness_goal to ENUM type
    logger.info("Converting meal_plans.fitness_goal to ENUM type...")

    # MySQL: ALTER TABLE meal_plans MODIFY fitness_goal ENUM('cut', 'bulk', 'recomp')
    op.alter_column(
        'meal_plans',
        'fitness_goal',
        existing_type=sa.String(length=20),
        type_=mysql.ENUM('cut', 'bulk', 'recomp', name='fitnessgoalenum'),
        existing_nullable=True
    )

    logger.info("✅ Successfully updated fitness_goal columns to cut/bulk/recomp")


def downgrade() -> None:
    """Revert fitness_goal columns back to old enum values.

    Reverts:
    - user_profiles.fitness_goal: Revert default to 'maintenance'
    - meal_plans.fitness_goal: Revert to String type
    - Revert data: recomp→maintenance, cut→cutting, bulk→bulking
    """

    # Step 1: Revert meal_plans.fitness_goal to String type
    logger.info("Reverting meal_plans.fitness_goal to String type...")
    op.alter_column(
        'meal_plans',
        'fitness_goal',
        existing_type=mysql.ENUM('cut', 'bulk', 'recomp', name='fitnessgoalenum'),
        type_=sa.String(length=20),
        existing_nullable=True
    )

    # Step 2: Revert data in meal_plans
    logger.info("Reverting fitness_goal values in meal_plans...")
    op.execute("""
        UPDATE meal_plans
        SET fitness_goal = CASE
            WHEN fitness_goal = 'recomp' THEN 'maintenance'
            WHEN fitness_goal = 'cut' THEN 'cutting'
            WHEN fitness_goal = 'bulk' THEN 'bulking'
            ELSE fitness_goal
        END
        WHERE fitness_goal IN ('recomp', 'cut', 'bulk')
    """)

    # Step 3: Revert default value for user_profiles.fitness_goal
    logger.info("Reverting user_profiles.fitness_goal default to 'maintenance'...")
    op.alter_column(
        'user_profiles',
        'fitness_goal',
        existing_type=sa.String(length=30),
        server_default='maintenance',
        nullable=False
    )

    # Step 4: Revert data in user_profiles
    logger.info("Reverting fitness_goal values in user_profiles...")
    op.execute("""
        UPDATE user_profiles
        SET fitness_goal = CASE
            WHEN fitness_goal = 'recomp' THEN 'maintenance'
            WHEN fitness_goal = 'cut' THEN 'cutting'
            WHEN fitness_goal = 'bulk' THEN 'bulking'
            ELSE fitness_goal
        END
        WHERE fitness_goal IN ('recomp', 'cut', 'bulk')
    """)

    logger.info("✅ Successfully reverted fitness_goal columns to old values")
