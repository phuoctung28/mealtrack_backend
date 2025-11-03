"""add_notification_tables

Revision ID: 008
Revises: 007
Create Date: 2025-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_fcm_tokens table
    op.create_table(
        'user_fcm_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # User relationship
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        # FCM token data
        sa.Column('fcm_token', sa.String(255), nullable=False, unique=True),
        sa.Column('device_type', sa.Enum('ios', 'android', name='device_type_enum'), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        
        # Indexes for performance
        sa.Index('idx_user_fcm_tokens_user_id', 'user_id'),
        sa.Index('idx_user_fcm_tokens_active', 'is_active', postgresql_where=sa.text('is_active = true')),
    )
    
    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # User relationship (one-to-one)
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        
        # Notification Type Toggles
        sa.Column('meal_reminders_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('water_reminders_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('sleep_reminders_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('progress_notifications_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('reengagement_notifications_enabled', sa.Boolean(), default=True, nullable=False),
        
        # Meal Reminder Timing (minutes from midnight: 0-1439)
        sa.Column('breakfast_time_minutes', sa.Integer(), sa.CheckConstraint('breakfast_time_minutes >= 0 AND breakfast_time_minutes < 1440')),
        sa.Column('lunch_time_minutes', sa.Integer(), sa.CheckConstraint('lunch_time_minutes >= 0 AND lunch_time_minutes < 1440')),
        sa.Column('dinner_time_minutes', sa.Integer(), sa.CheckConstraint('dinner_time_minutes >= 0 AND dinner_time_minutes < 1440')),
        
        # Water Reminder Settings
        sa.Column('water_reminder_interval_hours', sa.Integer(), default=2, nullable=False),
        
        # Sleep Reminder Timing (minutes from midnight)
        sa.Column('sleep_reminder_time_minutes', sa.Integer(), sa.CheckConstraint('sleep_reminder_time_minutes >= 0 AND sleep_reminder_time_minutes < 1440')),
        
        # Index for performance
        sa.Index('idx_notification_preferences_user_id', 'user_id'),
        
        # Constraints
        sa.CheckConstraint('water_reminder_interval_hours > 0', name='check_water_interval'),
    )


def downgrade() -> None:
    op.drop_table('notification_preferences')
    op.drop_table('user_fcm_tokens')
