"""Add notifications table and drop notification_sent_log.

Revision ID: 050
Revises: 049
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('notification_type', sa.String(30), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('scheduled_for_utc', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(10), nullable=False, server_default='pending'),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_unique_constraint(
        'uq_notification_per_user_type_date',
        'notifications',
        ['user_id', 'notification_type', 'scheduled_date'],
    )
    op.create_index(
        'idx_notifications_due',
        'notifications',
        ['scheduled_for_utc', 'status'],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        'idx_notifications_expires',
        'notifications',
        ['expires_at'],
        postgresql_where=sa.text("status != 'pending'"),
    )

    # Drop old dedup table
    op.drop_index('ix_sent_log_cleanup', table_name='notification_sent_log')
    op.drop_table('notification_sent_log')


def downgrade() -> None:
    op.drop_table('notifications')
    op.create_table(
        'notification_sent_log',
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('sent_minute', sa.String(16), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'notification_type', 'sent_minute'),
    )
    op.create_index('ix_sent_log_cleanup', 'notification_sent_log', ['sent_at'])
