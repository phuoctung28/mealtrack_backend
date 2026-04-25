"""Bridge migration for renumbering fix.

Production DB was at 055 before renumbering. This empty migration
maintains continuity so alembic doesn't try to downgrade.

Revision ID: 055
Revises: 054
"""
from alembic import op

revision = '055'
down_revision = '054'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
