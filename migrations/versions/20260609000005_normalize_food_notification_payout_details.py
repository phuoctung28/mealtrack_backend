"""Normalize food, notification, and payout details.

Revision ID: 20260609000005
Revises: 20260609000004
"""

import sqlalchemy as sa
from alembic import op

revision = "20260609000005"
down_revision = "20260609000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "food_reference_serving_sizes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "food_reference_id",
            sa.Integer(),
            sa.ForeignKey("food_reference.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("grams", sa.Float(), nullable=True),
        sa.Column("milliliters", sa.Float(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_food_reference_serving_sizes_ref_position",
        "food_reference_serving_sizes",
        ["food_reference_id", "position"],
    )

    op.create_table(
        "food_reference_nutrients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "food_reference_id",
            sa.Integer(),
            sa.ForeignKey("food_reference.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nutrient_key", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.UniqueConstraint(
            "food_reference_id",
            "nutrient_key",
            name="uq_food_reference_nutrient_key",
        ),
    )
    op.create_index(
        "idx_food_reference_nutrients_ref_key",
        "food_reference_nutrients",
        ["food_reference_id", "nutrient_key"],
    )

    op.add_column(
        "notifications",
        sa.Column(
            "context_schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    op.add_column("payout_requests", sa.Column("payment_account_type", sa.String(20)))
    op.add_column("payout_requests", sa.Column("payment_account_masked", sa.String(64)))
    op.add_column("payout_requests", sa.Column("payment_country", sa.String(2)))
    op.add_column("payout_requests", sa.Column("payment_currency", sa.String(3)))
    op.create_index(
        "idx_payout_requests_status_requested",
        "payout_requests",
        ["status", "requested_at"],
    )
    op.execute("""
        ALTER TABLE payout_requests
        ADD CONSTRAINT check_payout_requests_status
        CHECK (status IN ('pending', 'processing', 'completed', 'rejected'))
        NOT VALID
        """)
    op.execute("""
        ALTER TABLE payout_requests
        ADD CONSTRAINT check_payout_requests_payment_method
        CHECK (payment_method IN ('momo', 'bank'))
        NOT VALID
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION pg_temp.mt_float_or_null(value text)
        RETURNS double precision
        LANGUAGE sql
        IMMUTABLE
        AS $$
            SELECT CASE
                WHEN value ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN value::double precision
                ELSE NULL
            END
        $$;
        """)

    op.execute("""
        INSERT INTO food_reference_serving_sizes (
            food_reference_id,
            name,
            grams,
            milliliters,
            is_default,
            position
        )
        SELECT
            fr.id,
            left(COALESCE(item.value ->> 'name', item.value ->> 'label'), 100),
            pg_temp.mt_float_or_null(item.value ->> 'grams'),
            pg_temp.mt_float_or_null(
                COALESCE(item.value ->> 'milliliters', item.value ->> 'ml')
            ),
            COALESCE((item.value ->> 'is_default')::boolean, item.ordinality = 1),
            item.ordinality - 1
        FROM food_reference fr
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE
                WHEN fr.serving_sizes IS NOT NULL
                 AND jsonb_typeof(fr.serving_sizes::jsonb) = 'array'
                THEN fr.serving_sizes::jsonb
                ELSE '[]'::jsonb
            END
        ) WITH ORDINALITY AS item(value, ordinality)
        WHERE COALESCE(item.value ->> 'name', item.value ->> 'label') IS NOT NULL
        """)

    op.execute("""
        INSERT INTO food_reference_serving_sizes (
            food_reference_id,
            name,
            grams,
            milliliters,
            is_default,
            position
        )
        SELECT
            fr.id,
            left(fr.serving_size, 100),
            NULL,
            NULL,
            true,
            0
        FROM food_reference fr
        WHERE fr.serving_size IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM food_reference_serving_sizes rows
              WHERE rows.food_reference_id = fr.id
          )
        """)

    op.execute("""
        WITH source_rows AS (
            SELECT
                fr.id AS food_reference_id,
                nutrient.key AS nutrient_key,
                nutrient.value AS payload
            FROM food_reference fr
            CROSS JOIN LATERAL jsonb_each(
                CASE
                    WHEN fr.extra_nutrients IS NOT NULL
                     AND jsonb_typeof(fr.extra_nutrients::jsonb) = 'object'
                    THEN fr.extra_nutrients::jsonb
                    ELSE '{}'::jsonb
                END
            ) AS nutrient(key, value)
        ),
        parsed AS (
            SELECT
                food_reference_id,
                left(nutrient_key, 100) AS nutrient_key,
                CASE
                    WHEN jsonb_typeof(payload) = 'object'
                    THEN pg_temp.mt_float_or_null(payload ->> 'amount')
                    ELSE pg_temp.mt_float_or_null(payload #>> '{}')
                END AS amount,
                CASE
                    WHEN jsonb_typeof(payload) = 'object'
                    THEN left(payload ->> 'unit', 32)
                    ELSE NULL
                END AS unit
            FROM source_rows
        )
        INSERT INTO food_reference_nutrients (
            food_reference_id,
            nutrient_key,
            amount,
            unit
        )
        SELECT food_reference_id, nutrient_key, amount, unit
        FROM parsed
        WHERE amount IS NOT NULL
        ON CONFLICT (food_reference_id, nutrient_key) DO NOTHING
        """)

    op.execute("""
        UPDATE payout_requests
        SET
            payment_account_type = CASE
                WHEN payment_method = 'bank'
                THEN COALESCE(payment_details::jsonb ->> 'bank', 'bank')
                WHEN payment_method = 'momo' THEN 'phone'
                ELSE payment_method
            END,
            payment_account_masked = CASE
                WHEN payment_method = 'bank'
                 AND payment_details::jsonb ? 'account'
                THEN repeat(
                    '*',
                    greatest(length(payment_details::jsonb ->> 'account') - 4, 0)
                ) || right(payment_details::jsonb ->> 'account', 4)
                WHEN payment_method = 'momo'
                 AND payment_details::jsonb ? 'phone'
                THEN repeat(
                    '*',
                    greatest(length(payment_details::jsonb ->> 'phone') - 4, 0)
                ) || right(payment_details::jsonb ->> 'phone', 4)
                ELSE NULL
            END,
            payment_country = COALESCE(payment_details::jsonb ->> 'country', 'VN'),
            payment_currency = COALESCE(payment_details::jsonb ->> 'currency', 'VND')
        WHERE payment_details IS NOT NULL
        """)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE payout_requests DROP CONSTRAINT IF EXISTS "
        "check_payout_requests_payment_method"
    )
    op.execute(
        "ALTER TABLE payout_requests DROP CONSTRAINT IF EXISTS "
        "check_payout_requests_status"
    )
    op.drop_index(
        "idx_payout_requests_status_requested",
        table_name="payout_requests",
    )
    op.drop_column("payout_requests", "payment_currency")
    op.drop_column("payout_requests", "payment_country")
    op.drop_column("payout_requests", "payment_account_masked")
    op.drop_column("payout_requests", "payment_account_type")
    op.drop_column("notifications", "context_schema_version")
    op.drop_index(
        "idx_food_reference_nutrients_ref_key",
        table_name="food_reference_nutrients",
    )
    op.drop_table("food_reference_nutrients")
    op.drop_index(
        "idx_food_reference_serving_sizes_ref_position",
        table_name="food_reference_serving_sizes",
    )
    op.drop_table("food_reference_serving_sizes")
