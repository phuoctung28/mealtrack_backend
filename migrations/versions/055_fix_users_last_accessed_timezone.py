"""Fix users.last_accessed to use TIMESTAMPTZ.

The last_accessed column was declared as TIMESTAMP WITHOUT TIME ZONE while
the code uses utc_now() which returns timezone-aware datetimes. asyncpg
rejects mixing naive and aware datetimes.

Revision ID: 055
Revises: 054
"""
from alembic import op
import sqlalchemy as sa

revision = '055'
down_revision = '054'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'users', 'last_accessed',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using="last_accessed AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        'users', 'last_accessed',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="last_accessed AT TIME ZONE 'UTC'",
    )
