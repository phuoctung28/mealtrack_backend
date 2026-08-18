from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATION = Path(
    "migrations/versions/20260818000001_merge_catalog_browse_and_translation_heads.py"
)


def test_merge_revision_joins_catalog_and_translation_heads() -> None:
    text = MIGRATION.read_text()

    assert 'revision: str = "20260818000001"' in text
    assert '"20260816000005"' in text
    assert '"20260817000001"' in text


def test_alembic_heads_resolve_to_merge_revision() -> None:
    script_dir = ScriptDirectory.from_config(Config("alembic.ini"))

    assert script_dir.get_heads() == ["20260818000001"]
    assert script_dir.get_current_head() == "20260818000001"
