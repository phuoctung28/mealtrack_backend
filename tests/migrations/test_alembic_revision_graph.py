import re

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_graph_has_single_head() -> None:
    script_dir = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script_dir.get_heads()
    current_head = script_dir.get_current_head()

    assert heads == [current_head]
    assert current_head is not None
    assert re.fullmatch(r"\d{3}|\d{14}", current_head)
