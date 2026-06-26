"""Add Cloudflare embedding metadata to meal_image_cache.

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
    op.execute("TRUNCATE TABLE meal_image_cache")
    op.execute("DROP INDEX IF EXISTS meal_image_cache_text_emb_idx")
    op.execute(
        "ALTER TABLE meal_image_cache "
        "ALTER COLUMN text_embedding TYPE vector(768)"
    )
    op.execute(
        "CREATE INDEX meal_image_cache_text_emb_idx "
        "ON meal_image_cache USING hnsw (text_embedding vector_cosine_ops)"
    )
    op.add_column(
        "meal_image_cache",
        sa.Column("text_embedding_v2", Vector(768), nullable=True),
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
    op.execute("TRUNCATE TABLE meal_image_cache")
    op.execute("DROP INDEX IF EXISTS meal_image_cache_text_emb_v2_idx")
    op.drop_column("meal_image_cache", "embedding_model")
    op.drop_column("meal_image_cache", "embedding_provider")
    op.drop_column("meal_image_cache", "text_embedding_v2")
    op.execute("DROP INDEX IF EXISTS meal_image_cache_text_emb_idx")
    op.execute(
        "ALTER TABLE meal_image_cache "
        "ALTER COLUMN text_embedding TYPE vector(512)"
    )
    op.execute(
        "CREATE INDEX meal_image_cache_text_emb_idx "
        "ON meal_image_cache USING hnsw (text_embedding vector_cosine_ops)"
    )
