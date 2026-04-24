"""Add referral system tables.

Revision ID: 052
Revises: 051
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Referral codes — one per user, used as invite codes
    op.create_table(
        "referral_codes",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_referral_codes_code", "referral_codes", ["code"], unique=True)

    # Referral conversions — one per referred user
    op.create_table(
        "referral_conversions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "referrer_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "referred_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("code_used", sa.String(6), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("discount_applied", sa.Integer, nullable=True),
        sa.Column("commission_amount", sa.Integer, nullable=False, server_default="50000"),
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_referral_conversions_referrer",
        "referral_conversions",
        ["referrer_user_id"],
    )
    op.create_index(
        "ix_referral_conversions_referred",
        "referral_conversions",
        ["referred_user_id"],
        unique=True,
    )

    # Referral wallets — tracks balance and lifetime totals
    op.create_table(
        "referral_wallets",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("balance", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_revoked", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_withdrawn", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Payout requests — user-initiated withdrawal requests
    op.create_table(
        "payout_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("payment_details", JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("admin_note", sa.Text, nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payout_requests_user_id", "payout_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_payout_requests_user_id", table_name="payout_requests")
    op.drop_table("payout_requests")
    op.drop_table("referral_wallets")
    op.drop_index("ix_referral_conversions_referred", table_name="referral_conversions")
    op.drop_index("ix_referral_conversions_referrer", table_name="referral_conversions")
    op.drop_table("referral_conversions")
    op.drop_index("ix_referral_codes_code", table_name="referral_codes")
    op.drop_table("referral_codes")
