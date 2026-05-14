from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_graph_has_single_head() -> None:
    script_dir = ScriptDirectory.from_config(Config("alembic.ini"))

    assert script_dir.get_heads() == [script_dir.get_current_head()]
