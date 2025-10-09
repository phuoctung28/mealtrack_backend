"""add_subscriptions_table

Revision ID: f04b8926a1d5
Revises: 490f9b3ada53
Create Date: 2025-10-08 16:07:05.746089

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f04b8926a1d5'
down_revision: Union[str, None] = '490f9b3ada53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # User relationship
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        # RevenueCat data
        sa.Column('revenuecat_subscriber_id', sa.String(255), nullable=False, index=True),
        sa.Column('product_id', sa.String(255), nullable=False),  # "premium_monthly" or "premium_yearly"
        sa.Column('platform', sa.Enum('ios', 'android', 'web', name='platform_enum'), nullable=False),
        
        # Subscription status
        sa.Column('status', sa.Enum('active', 'expired', 'cancelled', 'billing_issue', name='subscription_status_enum'), 
                  nullable=False, server_default='active'),
        sa.Column('purchased_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        
        # Store metadata
        sa.Column('store_transaction_id', sa.String(255), nullable=True),
        sa.Column('is_sandbox', sa.Boolean(), default=False, nullable=False),
        
        # Indexes for performance
        sa.Index('idx_user_id_status', 'user_id', 'status'),
        sa.Index('idx_expires_at', 'expires_at'),
        sa.Index('idx_revenuecat_subscriber_id', 'revenuecat_subscriber_id'),
    )


def downgrade() -> None:
    op.drop_table('subscriptions')
    # MySQL doesn't need explicit enum cleanup