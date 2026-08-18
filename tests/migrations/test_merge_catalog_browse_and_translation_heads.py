from pathlib import Path

MIGRATION = Path(
    "migrations/versions/20260818000001_merge_catalog_browse_and_translation_heads.py"
)


def test_merge_revision_joins_catalog_and_translation_heads() -> None:
    text = MIGRATION.read_text()

    assert 'revision: str = "20260818000001"' in text
    assert '"20260816000005"' in text
    assert '"20260817000001"' in text
