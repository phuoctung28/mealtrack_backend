"""Add OpenAI v2 embedding metadata to meal_image_cache.

Revision ID: 060
Revises: 059
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal_image_cache",
        sa.Column("text_embedding_v2", Vector(512), nullable=True),
    )
    op.add_column(
        "meal_image_cache",
        sa.Column("embedding_provider", sa.Text(), nullable=True),
    )
    op.add_column(
        "meal_image_cache",
        sa.Column("embedding_model", sa.Text(), nullable=True),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS meal_image_cache_text_emb_v2_idx "
        "ON meal_image_cache USING hnsw (text_embedding_v2 vector_cosine_ops) "
        "WHERE text_embedding_v2 IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS meal_image_cache_text_emb_v2_idx")
    op.drop_column("meal_image_cache", "embedding_model")
    op.drop_column("meal_image_cache", "embedding_provider")
    op.drop_column("meal_image_cache", "text_embedding_v2")
