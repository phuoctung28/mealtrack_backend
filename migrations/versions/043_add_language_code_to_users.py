"""Add language_code column to users table.

Backfills from notification_preferences.language for existing users.

Revision ID: 043
Revises: 042
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '043'
down_revision = '042'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add language_code column with default 'en'
    op.add_column(
        'users',
        sa.Column(
            'language_code',
            sa.String(5),
            nullable=False,
            server_default='en'
        )
    )

    # Backfill from notification_preferences.language where available
    op.execute(
        """
        UPDATE users u
        INNER JOIN notification_preferences np ON u.id = np.user_id
        SET u.language_code = np.language
        WHERE np.language IS NOT NULL
          AND np.language != 'en'
          AND np.is_deleted = 0
        """
    )


def downgrade() -> None:
    op.drop_column('users', 'language_code')
