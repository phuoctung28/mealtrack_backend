"""Fix meal_image_cache vector dimension from 768 to 512.

gemini-embedding-2-preview defaults to 3072-d vectors; we constrain to 512
via output_dimensionality. Existing cache rows with 768-d vectors must be
cleared since dimensions must match for vector queries.

Revision ID: 055
Revises: 054
"""
from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("TRUNCATE TABLE meal_image_cache")
    op.execute("DROP INDEX IF EXISTS meal_image_cache_text_emb_idx")
    op.execute(
        "ALTER TABLE meal_image_cache "
        "ALTER COLUMN text_embedding TYPE vector(512)"
    )
    op.execute(
        "CREATE INDEX meal_image_cache_text_emb_idx "
        "ON meal_image_cache USING hnsw (text_embedding vector_cosine_ops)"
    )


def downgrade() -> None:
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
