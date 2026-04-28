"""Fix cheat_days and saved_suggestions DateTime columns to use TIMESTAMPTZ.

These columns were declared as TIMESTAMP WITHOUT TIME ZONE while the code
uses utc_now() which returns timezone-aware datetimes. asyncpg rejects mixing
naive and aware datetimes.

Revision ID: 056
Revises: 055
"""
from alembic import op
import sqlalchemy as sa

revision = '056'
down_revision = '055'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix cheat_days.marked_at
    op.alter_column(
        'cheat_days', 'marked_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="marked_at AT TIME ZONE 'UTC'",
    )

    # Fix saved_suggestions.saved_at
    op.alter_column(
        'saved_suggestions', 'saved_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="saved_at AT TIME ZONE 'UTC'",
    )

    # Fix saved_suggestions.created_at
    op.alter_column(
        'saved_suggestions', 'created_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        'cheat_days', 'marked_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="marked_at AT TIME ZONE 'UTC'",
    )

    op.alter_column(
        'saved_suggestions', 'saved_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="saved_at AT TIME ZONE 'UTC'",
    )

    op.alter_column(
        'saved_suggestions', 'created_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
