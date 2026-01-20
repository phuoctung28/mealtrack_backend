"""add_soft_delete_columns_for_account_deletion

Revision ID: 015
Revises: 014
Create Date: 2026-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import NoSuchTableError

# revision identifiers, used by Alembic.
revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    if not table_exists(table_name):
        return True  # Return True to skip adding column if table doesn't exist
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    if not table_exists(table_name):
        return True  # Return True to skip adding index if table doesn't exist
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    # Add deleted_at to users table (for audit trail)
    if not column_exists('users', 'deleted_at'):
        op.add_column('users',
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
        )
    # Create index for querying deleted users
    if table_exists('users') and not index_exists('users', 'ix_users_deleted_at'):
        op.create_index('ix_users_deleted_at', 'users', ['deleted_at'])

    # Add is_active to meal_plans table (if table exists)
    if table_exists('meal_plans') and not column_exists('meal_plans', 'is_active'):
        op.add_column('meal_plans',
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1')
        )
    if table_exists('meal_plans') and not index_exists('meal_plans', 'ix_meal_plans_is_active'):
        op.create_index('ix_meal_plans_is_active', 'meal_plans', ['is_active'])

    # Add is_active to conversations table (if table exists)
    if table_exists('conversations') and not column_exists('conversations', 'is_active'):
        op.add_column('conversations',
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1')
        )
    if table_exists('conversations') and not index_exists('conversations', 'ix_conversations_is_active'):
        op.create_index('ix_conversations_is_active', 'conversations', ['is_active'])

    # Add is_deleted to notification_preferences table (if table exists)
    if table_exists('notification_preferences') and not column_exists('notification_preferences', 'is_deleted'):
        op.add_column('notification_preferences',
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0')
        )


def downgrade() -> None:
    # Remove is_deleted from notification_preferences
    if table_exists('notification_preferences') and column_exists('notification_preferences', 'is_deleted'):
        op.drop_column('notification_preferences', 'is_deleted')

    # Remove is_active from conversations
    if table_exists('conversations'):
        if index_exists('conversations', 'ix_conversations_is_active'):
            op.drop_index('ix_conversations_is_active', table_name='conversations')
        if column_exists('conversations', 'is_active'):
            op.drop_column('conversations', 'is_active')

    # Remove is_active from meal_plans
    if table_exists('meal_plans'):
        if index_exists('meal_plans', 'ix_meal_plans_is_active'):
            op.drop_index('ix_meal_plans_is_active', table_name='meal_plans')
        if column_exists('meal_plans', 'is_active'):
            op.drop_column('meal_plans', 'is_active')

    # Remove deleted_at from users
    if table_exists('users'):
        if index_exists('users', 'ix_users_deleted_at'):
            op.drop_index('ix_users_deleted_at', table_name='users')
        if column_exists('users', 'deleted_at'):
            op.drop_column('users', 'deleted_at')
