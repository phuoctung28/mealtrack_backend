"""Add notification preferences support

Revision ID: 006
Revises: 005
Create Date: 2025-10-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add notification preferences and related tables"""
    
    # Add notification preference columns to user_profiles
    op.add_column('user_profiles', 
        sa.Column('notifications_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('user_profiles', 
        sa.Column('push_notifications_enabled', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('user_profiles', 
        sa.Column('email_notifications_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('user_profiles', 
        sa.Column('weekly_weight_reminder_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('user_profiles', 
        sa.Column('weekly_weight_reminder_day', sa.Integer(), server_default='0', nullable=False))
    op.add_column('user_profiles', 
        sa.Column('weekly_weight_reminder_time', sa.String(5), server_default='09:00', nullable=False))
    
    # Add constraints
    op.create_check_constraint(
        'check_reminder_day_range',
        'user_profiles',
        'weekly_weight_reminder_day >= 0 AND weekly_weight_reminder_day <= 6'
    )
    op.create_check_constraint(
        'check_reminder_time_format',
        'user_profiles',
        "weekly_weight_reminder_time ~ '^[0-2][0-9]:[0-5][0-9]$'"
    )
    
    # Create device_tokens table
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_token', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('device_info', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_check_constraint(
        'check_platform_valid',
        'device_tokens',
        "platform IN ('ios', 'android', 'web')"
    )
    op.create_unique_constraint('unique_device_token', 'device_tokens', ['device_token'])
    op.create_index('idx_device_tokens_user_id', 'device_tokens', ['user_id'])
    op.create_index('idx_device_tokens_active', 'device_tokens', ['user_id', 'is_active'])
    op.create_index('idx_device_tokens_last_used', 'device_tokens', ['last_used_at'])
    
    # Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('delivery_method', sa.String(20), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('device_token_id', sa.String(36), sa.ForeignKey('device_tokens.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('opened_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_check_constraint(
        'check_delivery_method_valid',
        'notification_logs',
        "delivery_method IN ('push', 'email')"
    )
    op.create_check_constraint(
        'check_status_valid',
        'notification_logs',
        "status IN ('pending', 'sent', 'delivered', 'failed', 'opened')"
    )
    op.create_check_constraint(
        'check_notification_type_valid',
        'notification_logs',
        "notification_type IN ('weight_reminder', 'meal_reminder', 'achievement', 'goal_progress', 'social', 'system')"
    )
    
    op.create_index('idx_notification_logs_user_id', 'notification_logs', ['user_id'])
    op.create_index('idx_notification_logs_type', 'notification_logs', ['notification_type'])
    op.create_index('idx_notification_logs_status', 'notification_logs', ['status'])
    op.create_index('idx_notification_logs_created_at', 'notification_logs', ['created_at'])
    op.create_index('idx_notification_logs_user_type', 'notification_logs', ['user_id', 'notification_type'])


def downgrade() -> None:
    """Remove notification preferences support"""
    
    # Drop tables
    op.drop_table('notification_logs')
    op.drop_table('device_tokens')
    
    # Remove columns from user_profiles
    op.drop_column('user_profiles', 'weekly_weight_reminder_time')
    op.drop_column('user_profiles', 'weekly_weight_reminder_day')
    op.drop_column('user_profiles', 'weekly_weight_reminder_enabled')
    op.drop_column('user_profiles', 'email_notifications_enabled')
    op.drop_column('user_profiles', 'push_notifications_enabled')
    op.drop_column('user_profiles', 'notifications_enabled')

