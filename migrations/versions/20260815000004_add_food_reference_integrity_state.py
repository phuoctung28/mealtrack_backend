"""Add versioned food-reference eligibility and its append-only ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815000004"
down_revision: str | None = "20260815000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONTROL_ID = 1
_POLICY_VERSION = "nutrition_integrity_v1"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Additive DDL must fail fast rather than hold a production lock.
        op.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
        op.execute(sa.text("SET LOCAL statement_timeout = '60s'"))
    inspector = sa.inspect(bind)
    if not inspector.has_table("food_reference"):
        return

    columns = {column["name"] for column in inspector.get_columns("food_reference")}
    for name, column in (
        ("integrity_status", sa.String(length=16)),
        ("integrity_policy_version", sa.String(length=64)),
        ("integrity_checked_at", sa.DateTime(timezone=True)),
        ("integrity_reason", sa.String(length=128)),
        ("integrity_input_digest", sa.String(length=64)),
        ("integrity_review_reference", sa.String(length=255)),
    ):
        if name not in columns:
            op.add_column(
                "food_reference",
                sa.Column(
                    name,
                    column,
                    nullable=name != "integrity_status",
                    server_default="unknown" if name == "integrity_status" else None,
                ),
            )

    if not inspector.has_table("food_reference_integrity_control"):
        op.create_table(
            "food_reference_integrity_control",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("active_policy_version", sa.String(length=64), nullable=False),
            sa.Column(
                "catalog_integrity_generation",
                sa.BigInteger(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("activation_run_id", sa.String(length=36), nullable=True),
            sa.Column("deployed_revision", sa.String(length=128), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.CheckConstraint("id = 1", name="ck_food_integrity_control_singleton"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.execute(
        sa.text(
            """
            INSERT INTO food_reference_integrity_control
                (id, active_policy_version, catalog_integrity_generation, updated_at)
            VALUES (:id, :policy, 0, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(id=_CONTROL_ID, policy=_POLICY_VERSION)
    )

    inspector = sa.inspect(bind)
    if not inspector.has_table("food_reference_integrity_events"):
        op.create_table(
            "food_reference_integrity_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("food_reference_id", sa.Integer(), nullable=False),
            sa.Column("before_status", sa.String(length=16), nullable=False),
            sa.Column("after_status", sa.String(length=16), nullable=False),
            sa.Column("reason_code", sa.String(length=64), nullable=False),
            sa.Column("policy_version", sa.String(length=64), nullable=True),
            sa.Column("input_digest", sa.String(length=64), nullable=True),
            sa.Column("actor_kind", sa.String(length=32), nullable=False),
            sa.Column("reviewer_principal_hmac", sa.String(length=128), nullable=True),
            sa.Column("approval_reference", sa.String(length=255), nullable=True),
            sa.Column("run_id", sa.String(length=36), nullable=True),
            sa.Column("operation_id", sa.String(length=255), nullable=True),
            sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
            sa.Column("deployed_revision", sa.String(length=128), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.CheckConstraint(
                "before_status IN ('unknown', 'valid', 'quarantined')",
                name="ck_food_integrity_event_before_status",
            ),
            sa.CheckConstraint(
                "after_status IN ('unknown', 'valid', 'quarantined')",
                name="ck_food_integrity_event_after_status",
            ),
            sa.ForeignKeyConstraint(
                ["food_reference_id"], ["food_reference.id"], name="fk_food_integrity_event_reference"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    event_indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("food_reference_integrity_events")
    }
    if "ix_food_reference_integrity_events_reference_created" not in event_indexes:
        op.create_index(
            "ix_food_reference_integrity_events_reference_created",
            "food_reference_integrity_events",
            ["food_reference_id", "created_at"],
        )

    _add_not_valid_checks(bind)
    if bind.dialect.name == "postgresql":
        _install_postgres_guards()


def _add_not_valid_checks(bind) -> None:
    if bind.dialect.name != "postgresql":
        return
    constraint_names = {
        check["name"]
        for check in sa.inspect(bind).get_check_constraints("food_reference")
    }
    if "ck_food_reference_integrity_status" not in constraint_names:
        op.execute(
            sa.text(
                """
                ALTER TABLE food_reference
                ADD CONSTRAINT ck_food_reference_integrity_status
                CHECK (integrity_status IN ('unknown', 'valid', 'quarantined')) NOT VALID
                """
            )
        )
    if "ck_food_reference_integrity_verified_bounds" not in constraint_names:
        op.execute(
            sa.text(
                """
                ALTER TABLE food_reference
                ADD CONSTRAINT ck_food_reference_integrity_verified_bounds
                CHECK (
                    NOT is_verified OR (
                        protein_100g IS NOT NULL AND protein_100g = protein_100g
                        AND protein_100g BETWEEN 0 AND 100
                        AND carbs_100g IS NOT NULL AND carbs_100g = carbs_100g
                        AND carbs_100g BETWEEN 0 AND 100
                        AND fat_100g IS NOT NULL AND fat_100g = fat_100g
                        AND fat_100g BETWEEN 0 AND 100
                        AND fiber_100g = fiber_100g AND fiber_100g BETWEEN 0 AND 100
                        AND sugar_100g = sugar_100g AND sugar_100g BETWEEN 0 AND 100
                        AND protein_100g + carbs_100g + fat_100g <= 110
                    )
                ) NOT VALID
                """
            )
        )

    if not sa.inspect(bind).has_table("food_reference_serving_sizes"):
        return
    child_checks = {
        check["name"]
        for check in sa.inspect(bind).get_check_constraints(
            "food_reference_serving_sizes"
        )
    }
    if "ck_food_serving_positive_conversion" not in child_checks:
        op.execute(
            sa.text(
                """
                ALTER TABLE food_reference_serving_sizes
                ADD CONSTRAINT ck_food_serving_positive_conversion
                CHECK (
                    (grams IS NOT NULL AND grams = grams AND grams > 0)
                    OR (milliliters IS NOT NULL AND milliliters = milliliters
                        AND milliliters > 0)
                ) NOT VALID
                """
            )
        )
    if "ck_food_serving_canonical_gram" not in child_checks:
        op.execute(
            sa.text(
                """
                ALTER TABLE food_reference_serving_sizes
                ADD CONSTRAINT ck_food_serving_canonical_gram
                CHECK (
                    lower(trim(name)) NOT IN ('g', 'gram', 'grams') OR grams = 1
                ) NOT VALID
                """
            )
        )


def _install_postgres_guards() -> None:
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION reject_food_integrity_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'food reference integrity events are append-only';
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_food_integrity_event_append_only
                ON food_reference_integrity_events;
            CREATE TRIGGER trg_food_integrity_event_append_only
            BEFORE UPDATE OR DELETE ON food_reference_integrity_events
            FOR EACH ROW EXECUTE FUNCTION reject_food_integrity_event_mutation();
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION invalidate_food_reference_integrity_from_serving()
            RETURNS trigger AS $$
            DECLARE
                reference_id integer;
                previous_status text;
                active_policy text;
            BEGIN
                reference_id := COALESCE(NEW.food_reference_id, OLD.food_reference_id);
                SELECT integrity_status INTO previous_status
                FROM food_reference WHERE id = reference_id FOR UPDATE;
                SELECT active_policy_version INTO active_policy
                FROM food_reference_integrity_control WHERE id = 1 FOR UPDATE;
                UPDATE food_reference
                SET integrity_status = 'unknown',
                    integrity_policy_version = NULL,
                    integrity_checked_at = NULL,
                    integrity_reason = 'serving_changed',
                    integrity_input_digest = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = reference_id;
                UPDATE food_reference_integrity_control
                SET catalog_integrity_generation = catalog_integrity_generation + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1;
                INSERT INTO food_reference_integrity_events (
                    id, food_reference_id, before_status, after_status,
                    reason_code, policy_version, actor_kind, created_at
                ) VALUES (
                    md5(random()::text || clock_timestamp()::text), reference_id,
                    COALESCE(previous_status, 'unknown'), 'unknown',
                    'serving_changed', active_policy, 'system', CURRENT_TIMESTAMP
                );
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_food_reference_serving_integrity
                ON food_reference_serving_sizes;
            CREATE TRIGGER trg_food_reference_serving_integrity
            AFTER INSERT OR UPDATE OR DELETE ON food_reference_serving_sizes
            FOR EACH ROW EXECUTE FUNCTION invalidate_food_reference_integrity_from_serving();
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("food_reference_integrity_events"):
        ledger_count = bind.execute(
            sa.text("SELECT COUNT(*) FROM food_reference_integrity_events")
        ).scalar_one()
        if ledger_count:
            # Never silently delete the append-only ledger during a rollback.
            raise RuntimeError("preserve the append-only ledger before downgrade")
        if bind.dialect.name == "postgresql":
            op.execute(
                sa.text(
                    """
                    DROP TRIGGER IF EXISTS trg_food_integrity_event_append_only
                        ON food_reference_integrity_events;
                    DROP TRIGGER IF EXISTS trg_food_reference_serving_integrity
                        ON food_reference_serving_sizes;
                    DROP FUNCTION IF EXISTS reject_food_integrity_event_mutation();
                    DROP FUNCTION IF EXISTS invalidate_food_reference_integrity_from_serving();
                    """
                )
            )
        if "ix_food_reference_integrity_events_reference_created" in {
            index["name"] for index in inspector.get_indexes("food_reference_integrity_events")
        }:
            op.drop_index(
                "ix_food_reference_integrity_events_reference_created",
                table_name="food_reference_integrity_events",
            )
        op.drop_table("food_reference_integrity_events")

    if inspector.has_table("food_reference_integrity_control"):
        op.drop_table("food_reference_integrity_control")

    if inspector.has_table("food_reference"):
        if bind.dialect.name == "postgresql":
            for name in (
                "ck_food_reference_integrity_status",
                "ck_food_reference_integrity_verified_bounds",
            ):
                if name in {
                    check["name"]
                    for check in sa.inspect(bind).get_check_constraints("food_reference")
                }:
                    op.drop_constraint(name, "food_reference", type_="check")
        columns = {column["name"] for column in sa.inspect(bind).get_columns("food_reference")}
        for name in (
            "integrity_review_reference",
            "integrity_input_digest",
            "integrity_reason",
            "integrity_checked_at",
            "integrity_policy_version",
            "integrity_status",
        ):
            if name in columns:
                op.drop_column("food_reference", name)
