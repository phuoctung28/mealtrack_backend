"""Normalize user profile preference arrays.

Revision ID: 20260609000002
Revises: 20260609000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260609000002"
down_revision = "20260609000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profile_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            sa.String(36),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("preference_type", sa.String(40), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "profile_id",
            "preference_type",
            "value",
            name="uq_user_profile_preference_value",
        ),
    )
    op.create_index(
        "idx_user_profile_preferences_position",
        "user_profile_preferences",
        ["profile_id", "preference_type", "position"],
    )

    op.execute("""
        WITH expanded AS (
            SELECT
                up.id AS profile_id,
                source.preference_type,
                trim(item.value) AS value,
                item.ordinality - 1 AS position,
                lower(trim(item.value)) AS normalized_value
            FROM user_profiles AS up
            CROSS JOIN LATERAL (
                VALUES
                    ('dietary_preferences', up.dietary_preferences),
                    ('health_conditions', up.health_conditions),
                    ('allergies', up.allergies),
                    ('pain_points', up.pain_points),
                    ('referral_sources', up.referral_sources),
                    ('training_types', up.training_types)
            ) AS source(preference_type, raw_values)
            CROSS JOIN LATERAL jsonb_array_elements_text(
                CASE
                    WHEN source.raw_values IS NOT NULL
                     AND jsonb_typeof(source.raw_values::jsonb) = 'array'
                    THEN source.raw_values::jsonb
                    ELSE '[]'::jsonb
                END
            ) WITH ORDINALITY AS item(value, ordinality)
            WHERE trim(item.value) <> ''
        ),
        deduped AS (
            SELECT DISTINCT ON (profile_id, preference_type, normalized_value)
                profile_id,
                preference_type,
                value,
                position
            FROM expanded
            ORDER BY profile_id, preference_type, normalized_value, position
        ),
        stable_ids AS (
            SELECT
                profile_id,
                preference_type,
                value,
                position,
                md5(profile_id || ':' || preference_type || ':' || lower(value)) AS hash
            FROM deduped
        )
        INSERT INTO user_profile_preferences (
            id,
            profile_id,
            preference_type,
            value,
            position,
            created_at,
            updated_at
        )
        SELECT
            substr(hash, 1, 8) || '-' ||
            substr(hash, 9, 4) || '-' ||
            substr(hash, 13, 4) || '-' ||
            substr(hash, 17, 4) || '-' ||
            substr(hash, 21, 12),
            profile_id,
            preference_type,
            value,
            position,
            now(),
            now()
        FROM stable_ids
        ON CONFLICT (profile_id, preference_type, value) DO NOTHING
        """)


def downgrade() -> None:
    op.drop_index(
        "idx_user_profile_preferences_position",
        table_name="user_profile_preferences",
    )
    op.drop_table("user_profile_preferences")
