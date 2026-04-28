"""Fix meal_image_cache vector dimension from 768 to 512.

gemini-embedding-2-preview returns 512-d vectors natively.
Existing cache rows with 768-d vectors must be truncated since they
cannot be queried with 512-d embeddings.

Revision ID: 056
Revises: 055
"""
from alembic import op

revision = "056"
down_revision = "055"
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
