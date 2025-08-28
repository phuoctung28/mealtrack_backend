"""Add seasonings column to planned_meal and user table enhancements

Revision ID: 002
Revises: 001
Create Date: 2024-08-28 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add seasonings column to planned_meal table and user table enhancements"""
    
    # Add seasonings column to planned_meals table
    op.add_column('planned_meals', sa.Column('seasonings', sa.JSON(), nullable=True))
    logger.info("✅ Added seasonings column to planned_meals table")
    
    # Add new columns to users table
    op.add_column('users', sa.Column('firebase_uid', sa.String(length=36), nullable=False))
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('photo_url', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('provider', sa.Enum('PHONE', 'GOOGLE', 'APPLE', name='authproviderenum'), nullable=False, server_default='PHONE'))
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('last_accessed', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()))
    logger.info("✅ Added user enhancement columns")
    
    # Add indexes for performance
    op.create_index('idx_firebase_uid', 'users', ['firebase_uid'])
    op.create_index('idx_provider', 'users', ['provider'])
    op.create_index('idx_onboarding_completed', 'users', ['onboarding_completed'])
    logger.info("✅ Created performance indexes")
    
    # Add unique constraint for firebase_uid
    op.create_unique_constraint('uq_users_firebase_uid', 'users', ['firebase_uid'])
    logger.info("✅ Added unique constraint for firebase_uid")


def downgrade() -> None:
    """Remove seasonings column from planned_meal table and user table enhancements"""
    
    # Remove unique constraint and indexes
    op.drop_constraint('uq_users_firebase_uid', 'users', type_='unique')
    op.drop_index('idx_onboarding_completed', table_name='users')
    op.drop_index('idx_provider', table_name='users')
    op.drop_index('idx_firebase_uid', table_name='users')
    logger.info("✅ Removed indexes and constraints")
    
    # Remove columns from users table
    op.drop_column('users', 'last_accessed')
    op.drop_column('users', 'onboarding_completed')
    op.drop_column('users', 'provider')
    op.drop_column('users', 'photo_url')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'firebase_uid')
    logger.info("✅ Removed user enhancement columns")
    
    # Remove seasonings column from planned_meals table
    op.drop_column('planned_meals', 'seasonings')
    logger.info("✅ Removed seasonings column from planned_meals table")