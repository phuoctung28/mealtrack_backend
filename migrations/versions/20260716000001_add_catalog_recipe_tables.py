"""Add immutable catalog recipe tables.

Revision ID: 20260716000001
Revises: 20260707000001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260716000001"
down_revision = "20260707000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_releases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("release_key", sa.String(length=120), nullable=False),
        sa.Column("manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expected_recipe_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'retired', 'failed')",
            name="ck_catalog_releases_status",
        ),
        sa.CheckConstraint(
            "expected_recipe_count > 0",
            name="ck_catalog_releases_expected_recipe_count_positive",
        ),
        sa.UniqueConstraint("release_key", name="uq_catalog_releases_release_key"),
        sa.UniqueConstraint(
            "manifest_digest",
            name="uq_catalog_releases_manifest_digest",
        ),
    )
    op.create_index(
        "idx_catalog_releases_status",
        "catalog_releases",
        ["status"],
    )
    op.create_index(
        "uq_catalog_releases_single_active",
        "catalog_releases",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "catalog_recipes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("recipe_key", sa.String(length=160), nullable=False),
        sa.Column("cuisine", sa.String(length=40), nullable=False),
        sa.Column("default_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint("length(recipe_key) > 0", name="ck_catalog_recipes_key"),
        sa.CheckConstraint("length(cuisine) > 0", name="ck_catalog_recipes_cuisine"),
        sa.UniqueConstraint("recipe_key", name="uq_catalog_recipes_recipe_key"),
    )
    op.create_index(
        "idx_catalog_recipes_cuisine_active",
        "catalog_recipes",
        ["cuisine", "is_active"],
    )

    op.create_table(
        "catalog_recipe_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "recipe_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "release_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_releases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("instructions", sa.JSON(), nullable=False),
        sa.Column("prep_minutes", sa.Integer(), nullable=True),
        sa.Column("cook_minutes", sa.Integer(), nullable=True),
        sa.Column("servings", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False),
        sa.Column("carbs_g", sa.Float(), nullable=False),
        sa.Column("fat_g", sa.Float(), nullable=False),
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sugar_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_revision", sa.String(length=120), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name="ck_catalog_recipe_versions_status",
        ),
        sa.CheckConstraint("version_number > 0", name="ck_catalog_versions_number"),
        sa.CheckConstraint("servings > 0", name="ck_catalog_versions_servings"),
        sa.CheckConstraint("calories >= 0", name="ck_catalog_versions_calories"),
        sa.CheckConstraint(
            "protein_g >= 0 AND carbs_g >= 0 AND fat_g >= 0 "
            "AND fiber_g >= 0 AND sugar_g >= 0",
            name="ck_catalog_versions_macros_non_negative",
        ),
        sa.CheckConstraint(
            "fiber_g <= carbs_g AND sugar_g <= carbs_g",
            name="ck_catalog_versions_fiber_sugar_bounds",
        ),
        sa.UniqueConstraint(
            "recipe_id",
            "version_number",
            name="uq_catalog_recipe_versions_recipe_version",
        ),
    )
    op.create_index(
        "idx_catalog_recipe_versions_release_status",
        "catalog_recipe_versions",
        ["release_id", "status"],
    )

    op.create_table(
        "catalog_recipe_version_meal_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("meal_type", sa.String(length=30), nullable=False),
        sa.UniqueConstraint(
            "version_id",
            "meal_type",
            name="uq_catalog_recipe_meal_types_version_type",
        ),
    )
    op.create_index(
        "idx_catalog_recipe_meal_types_type",
        "catalog_recipe_version_meal_types",
        ["meal_type"],
    )

    op.create_table(
        "catalog_recipe_ingredients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "food_reference_id",
            sa.Integer(),
            sa.ForeignKey("food_reference.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=False),
        sa.Column("resolved_grams", sa.Float(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False),
        sa.Column("carbs_g", sa.Float(), nullable=False),
        sa.Column("fat_g", sa.Float(), nullable=False),
        sa.Column("fiber_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sugar_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("serving_snapshot", sa.JSON(), nullable=True),
        sa.Column("source_revision", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_display_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("quantity > 0", name="ck_catalog_ingredients_quantity"),
        sa.CheckConstraint(
            "resolved_grams > 0",
            name="ck_catalog_ingredients_resolved_grams",
        ),
        sa.CheckConstraint(
            "protein_g >= 0 AND carbs_g >= 0 AND fat_g >= 0 "
            "AND fiber_g >= 0 AND sugar_g >= 0",
            name="ck_catalog_ingredients_macros_non_negative",
        ),
        sa.CheckConstraint(
            "fiber_g <= carbs_g AND sugar_g <= carbs_g",
            name="ck_catalog_ingredients_fiber_sugar_bounds",
        ),
        sa.UniqueConstraint(
            "version_id",
            "position",
            name="uq_catalog_recipe_ingredients_version_position",
        ),
    )
    op.create_index(
        "idx_catalog_recipe_ingredients_food_ref",
        "catalog_recipe_ingredients",
        ["food_reference_id"],
    )

    op.create_table(
        "catalog_recipe_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("license_name", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.CheckConstraint("length(source_type) > 0", name="ck_catalog_sources_type"),
    )
    op.create_index(
        "idx_catalog_recipe_sources_version",
        "catalog_recipe_sources",
        ["version_id"],
    )

    op.create_table(
        "catalog_recipe_rights_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "version_id",
            sa.String(length=36),
            sa.ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approver", sa.String(length=255), nullable=False),
        sa.Column("agreement_identifier", sa.String(length=160), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('approved', 'pending', 'rejected')",
            name="ck_catalog_rights_status",
        ),
    )
    op.create_index(
        "idx_catalog_recipe_rights_version_status",
        "catalog_recipe_rights_records",
        ["version_id", "status"],
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION require_catalog_approved_rights_before_publish()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.status = 'published'
                AND (TG_OP = 'INSERT' OR OLD.status <> 'published')
                AND NOT EXISTS (
                    SELECT 1
                    FROM catalog_recipe_rights_records rights
                    WHERE rights.version_id = NEW.id
                      AND rights.status = 'approved'
                      AND length(rights.agreement_identifier) > 0
                )
            THEN
                RAISE EXCEPTION 'published catalog recipe versions require approved rights';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_catalog_versions_publish_rights
        BEFORE INSERT OR UPDATE ON catalog_recipe_versions
        FOR EACH ROW
        EXECUTE FUNCTION require_catalog_approved_rights_before_publish();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_catalog_published_version_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') AND OLD.status = 'published' THEN
                RAISE EXCEPTION 'published catalog recipe versions are immutable';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_catalog_versions_immutable
        BEFORE UPDATE OR DELETE ON catalog_recipe_versions
        FOR EACH ROW
        EXECUTE FUNCTION prevent_catalog_published_version_mutation();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_catalog_published_child_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            parent_status text;
            parent_id text;
        BEGIN
            parent_id := COALESCE(NEW.version_id, OLD.version_id);
            SELECT status INTO parent_status
            FROM catalog_recipe_versions
            WHERE id = parent_id;

            IF parent_status = 'published' THEN
                RAISE EXCEPTION 'published catalog recipe children are immutable';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$;
    """)
    for table_name in (
        "catalog_recipe_version_meal_types",
        "catalog_recipe_ingredients",
        "catalog_recipe_sources",
        "catalog_recipe_rights_records",
    ):
        op.execute(f"""
            CREATE TRIGGER trg_{table_name}_immutable
            BEFORE INSERT OR UPDATE OR DELETE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION prevent_catalog_published_child_mutation();
        """)


def downgrade() -> None:
    for table_name in (
        "catalog_recipe_rights_records",
        "catalog_recipe_sources",
        "catalog_recipe_ingredients",
        "catalog_recipe_version_meal_types",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_catalog_versions_immutable "
        "ON catalog_recipe_versions"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_catalog_versions_publish_rights "
        "ON catalog_recipe_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS require_catalog_approved_rights_before_publish()")
    op.execute("DROP FUNCTION IF EXISTS prevent_catalog_published_child_mutation()")
    op.execute("DROP FUNCTION IF EXISTS prevent_catalog_published_version_mutation()")

    op.drop_table("catalog_recipe_rights_records")
    op.drop_table("catalog_recipe_sources")
    op.drop_table("catalog_recipe_ingredients")
    op.drop_table("catalog_recipe_version_meal_types")
    op.drop_table("catalog_recipe_versions")
    op.drop_table("catalog_recipes")
    op.drop_index("uq_catalog_releases_single_active", table_name="catalog_releases")
    op.drop_table("catalog_releases")
