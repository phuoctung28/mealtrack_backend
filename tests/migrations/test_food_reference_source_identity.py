from pathlib import Path

MIGRATION = next(
    Path("migrations/versions").glob("*_add_food_reference_source_identity.py")
)


def test_food_reference_source_identity_migration_adds_opaque_provider_identity():
    text = MIGRATION.read_text()

    assert '"source_namespace"' in text
    assert '"source_food_id"' in text
    assert "source_namespace IS NOT NULL" in text
    assert "source_food_id IS NOT NULL" in text
