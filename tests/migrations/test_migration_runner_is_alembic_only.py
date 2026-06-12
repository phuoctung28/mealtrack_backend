from pathlib import Path

RUNNER_PATH = Path(__file__).parents[2] / "migrations" / "run.py"


def test_migration_runner_does_not_create_schema_from_metadata() -> None:
    runner_text = RUNNER_PATH.read_text()

    assert "Base.metadata.create_all" not in runner_text
    assert "command.stamp" not in runner_text
    assert 'command.upgrade(alembic_cfg, "head")' in runner_text
