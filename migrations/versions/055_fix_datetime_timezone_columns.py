"""Fix meal and meal_translation timestamp columns to use TIMESTAMPTZ.

ready_at and last_edited_at on meal, and translated_at and created_at on
meal_translation were declared as TIMESTAMP WITHOUT TIME ZONE. All other
timestamp columns in the schema use TIMESTAMP WITH TIME ZONE. This converts
them consistently so asyncpg can accept timezone-aware datetimes without
the _to_naive_utc() workaround.

Revision ID: 055
Revises: 054
"""
from alembic import op
import sqlalchemy as sa

revision = '055'
down_revision = '054'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'meal', 'ready_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using='ready_at AT TIME ZONE \'UTC\'',
    )
    op.alter_column(
        'meal', 'last_edited_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=True,
        postgresql_using='last_edited_at AT TIME ZONE \'UTC\'',
    )
    op.alter_column(
        'meal_translation', 'translated_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using='translated_at AT TIME ZONE \'UTC\'',
    )
    op.alter_column(
        'meal_translation', 'created_at',
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
        postgresql_using='created_at AT TIME ZONE \'UTC\'',
    )


def downgrade() -> None:
    op.alter_column(
        'meal_translation', 'created_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using='created_at AT TIME ZONE \'UTC\'',
    )
    op.alter_column(
        'meal_translation', 'translated_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using='translated_at AT TIME ZONE \'UTC\'',
    )
    op.alter_column(
        'meal', 'last_edited_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using='last_edited_at AT TIME ZONE \'UTC\'',
    )
    op.alter_column(
        'meal', 'ready_at',
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using='ready_at AT TIME ZONE \'UTC\'',
    )
