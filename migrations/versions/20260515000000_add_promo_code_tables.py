"""Add promo_codes and promo_code_redemptions tables.

Revision ID: 20260515000000
Revises: 20260513070245
"""
import sqlalchemy as sa
from alembic import op

revision = "20260515000000"
down_revision = "20260513070245"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("max_uses", sa.Integer, nullable=False),
        sa.Column("current_uses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("rc_offering_id", sa.String(50), nullable=False, server_default=sa.text("'email'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"], unique=True)

    op.create_table(
        "promo_code_redemptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("promo_code_id", sa.String(36), sa.ForeignKey("promo_codes.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subscription_id", sa.String(36), sa.ForeignKey("subscriptions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("promo_code_id", "user_id", name="uq_promo_redemption_user"),
    )
    op.create_index("ix_promo_code_redemptions_promo_code_id", "promo_code_redemptions", ["promo_code_id"])
    op.create_index("ix_promo_code_redemptions_user_id", "promo_code_redemptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_promo_code_redemptions_user_id", table_name="promo_code_redemptions")
    op.drop_index("ix_promo_code_redemptions_promo_code_id", table_name="promo_code_redemptions")
    op.drop_table("promo_code_redemptions")
    op.drop_index("ix_promo_codes_code", table_name="promo_codes")
    op.drop_table("promo_codes")
