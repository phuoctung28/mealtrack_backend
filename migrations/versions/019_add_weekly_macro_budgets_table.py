"""add_weekly_macro_budgets_table

Revision ID: 019
Revises: 018
Create Date: 2026-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '019'
down_revision: Union[str, None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'weekly_macro_budgets',
        sa.Column('weekly_budget_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('target_calories', sa.Float(), nullable=False),
        sa.Column('target_protein', sa.Float(), nullable=False),
        sa.Column('target_carbs', sa.Float(), nullable=False),
        sa.Column('target_fat', sa.Float(), nullable=False),
        sa.Column('consumed_calories', sa.Float(), default=0.0, nullable=False),
        sa.Column('consumed_protein', sa.Float(), default=0.0, nullable=False),
        sa.Column('consumed_carbs', sa.Float(), default=0.0, nullable=False),
        sa.Column('consumed_fat', sa.Float(), default=0.0, nullable=False),
        sa.Column('cheat_slots_total', sa.Integer(), nullable=False),
        sa.Column('cheat_slots_used', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index('ix_weekly_macro_budgets_user_id', 'weekly_macro_budgets', ['user_id'])
    op.create_index('ix_weekly_macro_budgets_user_week', 'weekly_macro_budgets', ['user_id', 'week_start_date'])
    op.create_unique_constraint('uq_user_week', 'weekly_macro_budgets', ['user_id', 'week_start_date'])


def downgrade() -> None:
    op.drop_constraint('uq_user_week', 'weekly_macro_budgets', type_='unique')
    op.drop_index('ix_weekly_macro_budgets_user_week', table_name='weekly_macro_budgets')
    op.drop_index('ix_weekly_macro_budgets_user_id', table_name='weekly_macro_budgets')
    op.drop_table('weekly_macro_budgets')
