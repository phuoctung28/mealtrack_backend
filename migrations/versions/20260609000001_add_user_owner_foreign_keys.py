"""Add user ownership foreign keys.

Revision ID: 20260609000001
Revises: 20260531000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260609000001"
down_revision = "20260531000001"
branch_labels = None
depends_on = None


PRIVATE_ORPHAN_CLEANUP_SQL = (
    # Saved suggestions created with legacy Firebase UIDs are repaired to users.id.
    """
    UPDATE saved_suggestions AS ss
    SET user_id = users.id
    FROM users
    WHERE ss.user_id = users.firebase_uid
      AND ss.user_id <> users.id
    """,
    # Private user-owned rows cannot survive without a canonical owner.
    """
    DELETE FROM weekly_macro_budgets AS wmb
    WHERE NOT EXISTS (
        SELECT 1 FROM users WHERE users.id = wmb.user_id
    )
    """,
    """
    DELETE FROM cheat_days AS cd
    WHERE NOT EXISTS (
        SELECT 1 FROM users WHERE users.id = cd.user_id
    )
    """,
    """
    DELETE FROM saved_suggestions AS ss
    WHERE NOT EXISTS (
        SELECT 1 FROM users WHERE users.id = ss.user_id
    )
    """,
)


def upgrade() -> None:
    for statement in PRIVATE_ORPHAN_CLEANUP_SQL:
        op.execute(statement)

    op.alter_column(
        "saved_suggestions",
        "user_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=36),
        existing_nullable=False,
    )

    op.create_foreign_key(
        "fk_weekly_macro_budgets_user_id_users",
        "weekly_macro_budgets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_cheat_days_user_id_users",
        "cheat_days",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_saved_suggestions_user_id_users",
        "saved_suggestions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_saved_suggestions_user_id_users",
        "saved_suggestions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_cheat_days_user_id_users",
        "cheat_days",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_weekly_macro_budgets_user_id_users",
        "weekly_macro_budgets",
        type_="foreignkey",
    )

    op.alter_column(
        "saved_suggestions",
        "user_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
