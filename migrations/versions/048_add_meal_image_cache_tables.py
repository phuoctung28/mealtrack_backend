"""add_meal_image_cache_tables

Revision ID: 048
Revises: 047
Create Date: 2026-04-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '048'
down_revision: Union[str, None] = '047'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "meal_image_cache",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("meal_name", sa.Text, nullable=False),
        sa.Column("name_slug", sa.Text, nullable=False, unique=True),
        sa.Column("text_embedding", Vector(768), nullable=False),
        sa.Column("image_url", sa.Text, nullable=False),
        sa.Column("thumbnail_url", sa.Text, nullable=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    op.execute(
        "CREATE INDEX meal_image_cache_text_emb_idx "
        "ON meal_image_cache USING hnsw (text_embedding vector_cosine_ops)"
    )

    op.create_table(
        "pending_meal_image_resolution",
        sa.Column("name_slug", sa.Text, primary_key=True),
        sa.Column("meal_name", sa.Text, nullable=False),
        sa.Column("candidate_image_url", sa.Text, nullable=True),
        sa.Column("candidate_thumbnail_url", sa.Text, nullable=True),
        sa.Column("candidate_source", sa.Text, nullable=True),
        sa.Column("enqueued_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text, nullable=True),
    )
    op.create_index(
        "pending_meal_image_enqueued_at_idx",
        "pending_meal_image_resolution",
        ["enqueued_at"],
    )


def downgrade() -> None:
    op.drop_index("pending_meal_image_enqueued_at_idx",
                  table_name="pending_meal_image_resolution")
    op.drop_table("pending_meal_image_resolution")
    op.drop_index("meal_image_cache_text_emb_idx", table_name="meal_image_cache")
    op.drop_table("meal_image_cache")
    # Keep the vector extension installed
