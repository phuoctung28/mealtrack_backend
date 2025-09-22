"""convert_food_item_id_to_uuid

Revision ID: 490f9b3ada53
Revises: 004
Create Date: 2025-09-22 22:14:41.923129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '490f9b3ada53'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert the existing id column from integer to VARCHAR(36) for UUID storage
    # MySQL doesn't have native UUID type, so we use VARCHAR(36)
    op.execute("""
        ALTER TABLE food_item 
        MODIFY COLUMN id VARCHAR(36) NOT NULL DEFAULT (UUID())
    """)


def downgrade() -> None:
    # Convert UUID back to integer (this is destructive - original IDs are lost)
    # MySQL syntax for auto-incrementing integer
    op.execute("""
        ALTER TABLE food_item 
        MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT
    """)