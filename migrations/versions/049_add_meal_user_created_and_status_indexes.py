"""add_meal_user_created_and_status_indexes

Revision ID: 049
Revises: 048
Create Date: 2026-04-17 16:50:44.680534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '049'
down_revision: Union[str, None] = '048'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            'ix_meal_user_created',
            'meal',
            ['user_id', 'created_at'],
            postgresql_concurrently=True,
        )
        op.create_index(
            'ix_meal_status',
            'meal',
            ['status'],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index('ix_meal_status', table_name='meal', postgresql_concurrently=True)
        op.drop_index('ix_meal_user_created', table_name='meal', postgresql_concurrently=True)
