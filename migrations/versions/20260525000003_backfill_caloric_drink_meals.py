"""Backfill old caloric-drink meals: set meal_type='hydration', source='hydration'.

Old LogCaloricDrinkCommandHandler created meals with meal_type='snack' and
source='manual'. This migration fixes them so they appear as hydration in the
activities feed, consistent with newly-logged caloric drinks.

Revision ID: 20260525000003
Revises: 20260525000002
"""
from alembic import op

revision = "20260525000003"
down_revision = "20260525000002"
branch_labels = None
depends_on = None

# Base drink names from the catalog logged via the old caloric-drink flow.
# Old code stored "Milk tea · 500ml" (with volume suffix); new code stores "Milk tea".
_CALORIC_DRINK_PREFIXES = ("Milk tea", "Soda", "Fruit juice")


def upgrade() -> None:
    like_clauses = " OR ".join(
        f"dish_name LIKE '{name}%'" for name in _CALORIC_DRINK_PREFIXES
    )
    op.execute(f"""
        UPDATE meal
        SET meal_type = 'hydration',
            source    = 'hydration'
        WHERE source    = 'manual'
          AND meal_type = 'snack'
          AND ({like_clauses})
    """)


def downgrade() -> None:
    like_clauses = " OR ".join(
        f"dish_name LIKE '{name}%'" for name in _CALORIC_DRINK_PREFIXES
    )
    op.execute(f"""
        UPDATE meal
        SET meal_type = 'snack',
            source    = 'manual'
        WHERE source    = 'hydration'
          AND meal_type = 'hydration'
          AND quantity  IS NULL
          AND ({like_clauses})
    """)
