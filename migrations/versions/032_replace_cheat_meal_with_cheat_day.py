"""replace_cheat_meal_with_cheat_day

Revision ID: 032
Revises: 031
Create Date: 2026-03-08 17:31:04.644342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '032'
down_revision: Union[str, None] = '031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create cheat_days table
    op.create_table(
        'cheat_days',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('marked_at', sa.DateTime, nullable=False),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_cheat_date'),
    )
    op.create_index('ix_cheat_days_user_id', 'cheat_days', ['user_id'])
    op.create_index('ix_user_cheat_date', 'cheat_days', ['user_id', 'date'])

    # 2. Drop cheat_slots columns from weekly_macro_budgets (if they exist)
    # These were added as part of the old cheat meal system
    with op.batch_alter_table('weekly_macro_budgets') as batch_op:
        try:
            batch_op.drop_column('cheat_slots_total')
        except Exception:
            pass  # Column may already be absent
        try:
            batch_op.drop_column('cheat_slots_used')
        except Exception:
            pass  # Column may already be absent

    # 3. Drop is_cheat_meal and cheat_tagged_at from meal table (if they exist)
    with op.batch_alter_table('meal') as batch_op:
        try:
            batch_op.drop_column('is_cheat_meal')
        except Exception:
            pass  # Column may already be absent
        try:
            batch_op.drop_column('cheat_tagged_at')
        except Exception:
            pass  # Column may already be absent


def downgrade() -> None:
    # Remove cheat_days table
    op.drop_index('ix_user_cheat_date', table_name='cheat_days')
    op.drop_index('ix_cheat_days_user_id', table_name='cheat_days')
    op.drop_table('cheat_days')

    # Restore cheat_slots columns on weekly_macro_budgets
    with op.batch_alter_table('weekly_macro_budgets') as batch_op:
        batch_op.add_column(sa.Column('cheat_slots_total', sa.Integer, nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('cheat_slots_used', sa.Integer, nullable=False, server_default='0'))

    # Restore cheat meal columns on meal
    with op.batch_alter_table('meal') as batch_op:
        batch_op.add_column(sa.Column('is_cheat_meal', sa.Boolean, nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('cheat_tagged_at', sa.DateTime, nullable=True))
