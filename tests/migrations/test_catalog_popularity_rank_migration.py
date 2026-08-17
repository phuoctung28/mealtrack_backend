from pathlib import Path

MIGRATION = Path("migrations/versions/20260816000005_add_catalog_popularity_rank.py")


def test_catalog_popularity_rank_migration_is_forward_only_additive():
    text = MIGRATION.read_text()

    assert 'revision: str = "20260816000005"' in text
    assert 'down_revision: str | None = "20260815000004"' in text
    assert 'sa.Column("popularity_rank", sa.Integer(), nullable=True)' in text
    assert '"idx_meal_catalog_active_popularity"' in text
    assert "ck_meal_catalog_popularity_rank_non_negative" in text
