"""add_email_fields_and_logs

Revision ID: 20260509230545
Revises: 20260503113601
Create Date: 2026-05-09 23:05:45.166121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260509230545'
down_revision: Union[str, None] = '20260503113601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email preference columns to users table
    op.add_column(
        'users',
        sa.Column('welcome_email_sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column(
            'email_opt_out',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )

    # Create email_logs table
    op.create_table(
        'email_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'user_id',
            sa.String(36),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('email_type', sa.String(50), nullable=False),
        sa.Column(
            'sent_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.Column('resend_message_id', sa.String(255), nullable=True),
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default=sa.text("'sent'"),
        ),
    )
    op.create_index(
        'idx_email_logs_user_type', 'email_logs', ['user_id', 'email_type']
    )
    op.create_index('idx_email_logs_sent_at', 'email_logs', ['sent_at'])


def downgrade() -> None:
    op.drop_index('idx_email_logs_sent_at', table_name='email_logs')
    op.drop_index('idx_email_logs_user_type', table_name='email_logs')
    op.drop_table('email_logs')
    op.drop_column('users', 'email_opt_out')
    op.drop_column('users', 'welcome_email_sent_at')
