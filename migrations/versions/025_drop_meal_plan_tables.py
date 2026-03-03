"""drop_meal_plan_tables

Revision ID: 5180b1a13e5b
Revises: 024
Create Date: 2026-03-02 17:30:27.910463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5180b1a13e5b'
down_revision: Union[str, None] = '024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop meal plan hierarchy in child-to-parent order to satisfy FKs
    op.drop_table('planned_meals')
    op.drop_table('meal_plan_days')
    op.drop_table('meal_plans')


def downgrade() -> None:
    # Recreate meal plan tables in parent-to-child order

    op.create_table(
        'meal_plans',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('dietary_preferences', sa.JSON(), nullable=True),
        sa.Column('allergies', sa.JSON(), nullable=True),
        sa.Column('fitness_goal', sa.String(length=20), nullable=True),
        sa.Column('meals_per_day', sa.Integer(), nullable=True),
        sa.Column('snacks_per_day', sa.Integer(), nullable=True),
        sa.Column('cooking_time_weekday', sa.Integer(), nullable=True),
        sa.Column('cooking_time_weekend', sa.Integer(), nullable=True),
        sa.Column('favorite_cuisines', sa.JSON(), nullable=True),
        sa.Column('disliked_ingredients', sa.JSON(), nullable=True),
        sa.Column('plan_duration', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_meal_plans_user_id', 'meal_plans', ['user_id'])
    op.create_index('ix_meal_plans_is_active', 'meal_plans', ['is_active'])

    op.create_table(
        'meal_plan_days',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('meal_plan_id', sa.CHAR(length=36), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plans.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'planned_meals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('day_id', sa.Integer(), nullable=False),
        sa.Column('meal_type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prep_time', sa.Integer(), nullable=True),
        sa.Column('cook_time', sa.Integer(), nullable=True),
        sa.Column('calories', sa.Integer(), nullable=True),
        sa.Column('protein', sa.Float(), nullable=True),
        sa.Column('carbs', sa.Float(), nullable=True),
        sa.Column('fat', sa.Float(), nullable=True),
        sa.Column('ingredients', sa.JSON(), nullable=True),
        sa.Column('seasonings', sa.JSON(), nullable=True),
        sa.Column('instructions', sa.JSON(), nullable=True),
        sa.Column('is_vegetarian', sa.Boolean(), nullable=True),
        sa.Column('is_vegan', sa.Boolean(), nullable=True),
        sa.Column('is_gluten_free', sa.Boolean(), nullable=True),
        sa.Column('cuisine_type', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['day_id'], ['meal_plan_days.id']),
        sa.PrimaryKeyConstraint('id'),
    )

