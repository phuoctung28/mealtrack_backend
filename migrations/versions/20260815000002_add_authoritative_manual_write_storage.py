"""Store manual-save source snapshots and durable idempotency leases."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815000002"
down_revision: str | None = "20260815000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("food_item"):
        columns = {column["name"] for column in inspector.get_columns("food_item")}
        for name, column in (
            ("source_kind", sa.String(length=32)),
            ("source_food_id", sa.String(length=255)),
            ("nutrition_contract_version", sa.String(length=64)),
            ("source_snapshot", sa.JSON()),
        ):
            if name not in columns:
                op.add_column("food_item", sa.Column(name, column, nullable=True))

    if not inspector.has_table("meal_write_operation"):
        op.create_table(
            "meal_write_operation",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("operation", sa.String(length=64), nullable=False),
            sa.Column("idempotency_key", sa.String(length=255), nullable=False),
            sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("lease_owner", sa.String(length=36), nullable=True),
            sa.Column("lease_generation", sa.Integer(), nullable=False),
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("target_meal_id", sa.String(length=36), nullable=True),
            sa.Column("response", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "operation",
                "idempotency_key",
                name="uq_meal_write_operation_user_key",
            ),
        )
    indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("meal_write_operation")
    }
    if "ix_meal_write_operation_status_updated_at" not in indexes:
        op.create_index(
            "ix_meal_write_operation_status_updated_at",
            "meal_write_operation",
            ["status", "updated_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("meal_write_operation"):
        indexes = {
            index["name"]
            for index in sa.inspect(bind).get_indexes("meal_write_operation")
        }
        if "ix_meal_write_operation_status_updated_at" in indexes:
            op.drop_index(
                "ix_meal_write_operation_status_updated_at",
                table_name="meal_write_operation",
            )
        op.drop_table("meal_write_operation")

    if inspector.has_table("food_item"):
        columns = {column["name"] for column in inspector.get_columns("food_item")}
        for name in (
            "source_snapshot",
            "nutrition_contract_version",
            "source_food_id",
            "source_kind",
        ):
            if name in columns:
                op.drop_column("food_item", name)
