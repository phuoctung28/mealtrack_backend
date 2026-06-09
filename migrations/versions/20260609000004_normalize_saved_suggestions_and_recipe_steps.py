"""Normalize saved suggestions and recipe steps.

Revision ID: 20260609000004
Revises: 20260609000003
"""

import sqlalchemy as sa
from alembic import op

revision = "20260609000004"
down_revision = "20260609000003"
branch_labels = None
depends_on = None


def _uuid_from_expr(expr: str) -> str:
    return (
        f"substr(md5({expr}), 1, 8) || '-' || "
        f"substr(md5({expr}), 9, 4) || '-' || "
        f"substr(md5({expr}), 13, 4) || '-' || "
        f"substr(md5({expr}), 17, 4) || '-' || "
        f"substr(md5({expr}), 21, 12)"
    )


def upgrade() -> None:
    op.add_column("saved_suggestions", sa.Column("dish_name", sa.String(255)))
    op.add_column("saved_suggestions", sa.Column("description", sa.Text()))
    op.add_column("saved_suggestions", sa.Column("protein_g", sa.Float()))
    op.add_column("saved_suggestions", sa.Column("carbs_g", sa.Float()))
    op.add_column("saved_suggestions", sa.Column("fat_g", sa.Float()))
    op.add_column("saved_suggestions", sa.Column("fiber_g", sa.Float()))
    op.add_column("saved_suggestions", sa.Column("sugar_g", sa.Float()))
    op.add_column("saved_suggestions", sa.Column("language", sa.String(10)))

    op.create_table(
        "saved_suggestion_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "saved_suggestion_id",
            sa.String(36),
            sa.ForeignKey("saved_suggestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float()),
        sa.Column("unit", sa.String(64)),
        sa.Column("protein_g", sa.Float()),
        sa.Column("carbs_g", sa.Float()),
        sa.Column("fat_g", sa.Float()),
        sa.Column("fiber_g", sa.Float()),
        sa.Column("sugar_g", sa.Float()),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index(
        "idx_saved_suggestion_items_suggestion_position",
        "saved_suggestion_items",
        ["saved_suggestion_id", "position"],
    )

    op.create_table(
        "saved_suggestion_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "saved_suggestion_id",
            sa.String(36),
            sa.ForeignKey("saved_suggestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index(
        "idx_saved_suggestion_steps_suggestion_position",
        "saved_suggestion_steps",
        ["saved_suggestion_id", "position"],
    )

    op.create_table(
        "meal_instruction_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "meal_id",
            sa.String(36),
            sa.ForeignKey("meal.meal_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index(
        "idx_meal_instruction_steps_meal_position",
        "meal_instruction_steps",
        ["meal_id", "position"],
    )

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
        UPDATE saved_suggestions
        SET
            dish_name = COALESCE(
                suggestion_data::jsonb ->> 'dish_name',
                suggestion_data::jsonb ->> 'name',
                suggestion_data::jsonb ->> 'title'
            ),
            description = COALESCE(
                suggestion_data::jsonb ->> 'description',
                suggestion_data::jsonb ->> 'summary'
            ),
            language = COALESCE(
                suggestion_data::jsonb ->> 'language',
                suggestion_data::jsonb ->> 'locale'
            ),
            protein_g = COALESCE(
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'protein'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'protein_g'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{macros,protein}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,protein}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,protein_g}')
            ),
            carbs_g = COALESCE(
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'carbs'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'carbs_g'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{macros,carbs}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,carbs}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,carbs_g}')
            ),
            fat_g = COALESCE(
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'fat'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'fat_g'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{macros,fat}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,fat}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,fat_g}')
            ),
            fiber_g = COALESCE(
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'fiber'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'fiber_g'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{macros,fiber}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,fiber}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,fiber_g}')
            ),
            sugar_g = COALESCE(
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'sugar'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb ->> 'sugar_g'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{macros,sugar}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,sugar}'),
                pg_temp.mt_float_or_null(suggestion_data::jsonb #>> '{nutrition,sugar_g}')
            )
        WHERE suggestion_data IS NOT NULL
        """)

    item_id_expr = _uuid_from_expr("saved_suggestion_id || ':item:' || position::text")
    op.execute(f"""
        WITH source_rows AS (
            SELECT
                ss.id AS saved_suggestion_id,
                item.value AS payload,
                item.ordinality - 1 AS position
            FROM saved_suggestions ss
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(ss.suggestion_data::jsonb -> 'ingredients') = 'array'
                    THEN ss.suggestion_data::jsonb -> 'ingredients'
                    WHEN jsonb_typeof(ss.suggestion_data::jsonb -> 'items') = 'array'
                    THEN ss.suggestion_data::jsonb -> 'items'
                    WHEN jsonb_typeof(ss.suggestion_data::jsonb -> 'food_items') = 'array'
                    THEN ss.suggestion_data::jsonb -> 'food_items'
                    ELSE '[]'::jsonb
                END
            ) WITH ORDINALITY AS item(value, ordinality)
        ),
        parsed AS (
            SELECT
                saved_suggestion_id,
                payload,
                position,
                CASE
                    WHEN jsonb_typeof(payload) = 'string' THEN trim(payload #>> '{{}}')
                    WHEN jsonb_typeof(payload) = 'object' THEN trim(COALESCE(
                        payload ->> 'name',
                        payload ->> 'ingredient',
                        payload ->> 'food',
                        ''
                    ))
                    ELSE ''
                END AS name
            FROM source_rows
        )
        INSERT INTO saved_suggestion_items (
            id,
            saved_suggestion_id,
            name,
            quantity,
            unit,
            protein_g,
            carbs_g,
            fat_g,
            fiber_g,
            sugar_g,
            position
        )
        SELECT
            {item_id_expr},
            saved_suggestion_id,
            left(name, 255),
            CASE
                WHEN COALESCE(payload ->> 'quantity', payload ->> 'amount', payload ->> 'serving') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                THEN COALESCE(payload ->> 'quantity', payload ->> 'amount', payload ->> 'serving')::float
                ELSE NULL
            END,
            left(COALESCE(payload ->> 'unit', payload ->> 'measure'), 64),
            pg_temp.mt_float_or_null(COALESCE(payload ->> 'protein', payload ->> 'protein_g', payload #>> '{{macros,protein}}')),
            pg_temp.mt_float_or_null(COALESCE(payload ->> 'carbs', payload ->> 'carbs_g', payload #>> '{{macros,carbs}}')),
            pg_temp.mt_float_or_null(COALESCE(payload ->> 'fat', payload ->> 'fat_g', payload #>> '{{macros,fat}}')),
            pg_temp.mt_float_or_null(COALESCE(payload ->> 'fiber', payload ->> 'fiber_g', payload #>> '{{macros,fiber}}')),
            pg_temp.mt_float_or_null(COALESCE(payload ->> 'sugar', payload ->> 'sugar_g', payload #>> '{{macros,sugar}}')),
            position
        FROM parsed
        WHERE name <> ''
        ON CONFLICT (id) DO NOTHING
        """)

    step_id_expr = _uuid_from_expr("saved_suggestion_id || ':step:' || position::text")
    op.execute(f"""
        WITH source_rows AS (
            SELECT
                ss.id AS saved_suggestion_id,
                step.value AS payload,
                step.ordinality - 1 AS position
            FROM saved_suggestions ss
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(ss.suggestion_data::jsonb -> 'instructions') = 'array'
                    THEN ss.suggestion_data::jsonb -> 'instructions'
                    WHEN jsonb_typeof(ss.suggestion_data::jsonb -> 'steps') = 'array'
                    THEN ss.suggestion_data::jsonb -> 'steps'
                    WHEN jsonb_typeof(ss.suggestion_data::jsonb -> 'cooking_instructions') = 'array'
                    THEN ss.suggestion_data::jsonb -> 'cooking_instructions'
                    ELSE '[]'::jsonb
                END
            ) WITH ORDINALITY AS step(value, ordinality)
        ),
        parsed AS (
            SELECT
                saved_suggestion_id,
                payload,
                position,
                CASE
                    WHEN jsonb_typeof(payload) = 'string' THEN trim(payload #>> '{{}}')
                    WHEN jsonb_typeof(payload) = 'object' THEN trim(COALESCE(
                        payload ->> 'instruction',
                        payload ->> 'text',
                        payload ->> 'description',
                        ''
                    ))
                    ELSE ''
                END AS instruction
            FROM source_rows
        )
        INSERT INTO saved_suggestion_steps (
            id,
            saved_suggestion_id,
            instruction,
            duration_minutes,
            position
        )
        SELECT
            {step_id_expr},
            saved_suggestion_id,
            instruction,
            CASE
                WHEN COALESCE(payload ->> 'duration_minutes', payload ->> 'minutes') ~ '^[0-9]+$'
                THEN COALESCE(payload ->> 'duration_minutes', payload ->> 'minutes')::int
                ELSE NULL
            END,
            position
        FROM parsed
        WHERE instruction <> ''
        ON CONFLICT (id) DO NOTHING
        """)

    meal_step_id_expr = _uuid_from_expr("meal_id || ':step:' || position::text")
    op.execute(f"""
        WITH source_rows AS (
            SELECT
                m.meal_id,
                step.value AS payload,
                step.ordinality - 1 AS position
            FROM meal m
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN m.instructions IS NOT NULL
                     AND jsonb_typeof(m.instructions::jsonb) = 'array'
                    THEN m.instructions::jsonb
                    ELSE '[]'::jsonb
                END
            ) WITH ORDINALITY AS step(value, ordinality)
        ),
        parsed AS (
            SELECT
                meal_id,
                payload,
                position,
                CASE
                    WHEN jsonb_typeof(payload) = 'string' THEN trim(payload #>> '{{}}')
                    WHEN jsonb_typeof(payload) = 'object' THEN trim(COALESCE(
                        payload ->> 'instruction',
                        payload ->> 'text',
                        payload ->> 'description',
                        ''
                    ))
                    ELSE ''
                END AS instruction
            FROM source_rows
        )
        INSERT INTO meal_instruction_steps (
            id,
            meal_id,
            instruction,
            duration_minutes,
            position
        )
        SELECT
            {meal_step_id_expr},
            meal_id,
            instruction,
            CASE
                WHEN COALESCE(payload ->> 'duration_minutes', payload ->> 'minutes') ~ '^[0-9]+$'
                THEN COALESCE(payload ->> 'duration_minutes', payload ->> 'minutes')::int
                ELSE NULL
            END,
            position
        FROM parsed
        WHERE instruction <> ''
        ON CONFLICT (id) DO NOTHING
        """)


def downgrade() -> None:
    op.drop_index(
        "idx_meal_instruction_steps_meal_position",
        table_name="meal_instruction_steps",
    )
    op.drop_table("meal_instruction_steps")
    op.drop_index(
        "idx_saved_suggestion_steps_suggestion_position",
        table_name="saved_suggestion_steps",
    )
    op.drop_table("saved_suggestion_steps")
    op.drop_index(
        "idx_saved_suggestion_items_suggestion_position",
        table_name="saved_suggestion_items",
    )
    op.drop_table("saved_suggestion_items")
    op.drop_column("saved_suggestions", "language")
    op.drop_column("saved_suggestions", "sugar_g")
    op.drop_column("saved_suggestions", "fiber_g")
    op.drop_column("saved_suggestions", "fat_g")
    op.drop_column("saved_suggestions", "carbs_g")
    op.drop_column("saved_suggestions", "protein_g")
    op.drop_column("saved_suggestions", "description")
    op.drop_column("saved_suggestions", "dish_name")
