"""Baseline for existing database

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00

This is a baseline migration for a database that already has tables.
It does nothing on upgrade because tables were created by Base.metadata.create_all().

To mark your existing database as being at this revision:
    alembic stamp 001

This tells Alembic "the database is already at revision 001" without running any SQL.
Future migrations will build on this baseline.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Empty upgrade because database tables already exist.
    
    This migration represents the current state of an existing database
    that was created using Base.metadata.create_all().
    
    DO NOT run 'alembic upgrade head' on existing databases!
    Instead use: 'alembic stamp 001'
    """
    pass


def downgrade() -> None:
    """
    Cannot downgrade from initial baseline.
    To reset, drop and recreate the database.
    """
    pass