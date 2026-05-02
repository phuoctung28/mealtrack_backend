"""add_refunded_to_subscription_status and fix datetime columns

Revision ID: 054
Revises: 053
Create Date: 2026-04-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '054'
down_revision: Union[str, None] = '053'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: subscription_status_enum type doesn't exist — status column uses VARCHAR with native_enum=False
    # No ALTER TYPE needed; 'refunded' value works automatically with VARCHAR storage

    # Fix subscription datetime columns to use TIMESTAMPTZ (same fix as migration 052)
    op.alter_column(
        'subscriptions', 'purchased_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="purchased_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'subscriptions', 'expires_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'subscriptions', 'cancelled_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using="cancelled_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        'subscriptions', 'cancelled_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="cancelled_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'subscriptions', 'expires_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'subscriptions', 'purchased_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="purchased_at AT TIME ZONE 'UTC'",
    )
