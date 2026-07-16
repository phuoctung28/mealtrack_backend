"""Database models for immutable meal recommendation catalog recipes."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from src.infra.database.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CatalogReleaseORM(Base):
    """Versioned catalog release that controls runtime visibility."""

    __tablename__ = "catalog_releases"

    id = Column(String(36), primary_key=True, default=_uuid)
    release_key = Column(String(120), nullable=False, unique=True)
    manifest_digest = Column(String(64), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="draft")
    expected_recipe_count = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions = relationship(
        "CatalogRecipeVersionORM",
        back_populates="release",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'retired', 'failed')",
            name="ck_catalog_releases_status",
        ),
        CheckConstraint(
            "expected_recipe_count > 0",
            name="ck_catalog_releases_expected_recipe_count_positive",
        ),
        Index("idx_catalog_releases_status", "status"),
    )


class CatalogRecipeORM(Base):
    """Stable recipe identity across immutable versions."""

    __tablename__ = "catalog_recipes"

    id = Column(String(36), primary_key=True, default=_uuid)
    recipe_key = Column(String(160), nullable=False, unique=True)
    cuisine = Column(String(40), nullable=False)
    default_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions = relationship(
        "CatalogRecipeVersionORM",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("length(recipe_key) > 0", name="ck_catalog_recipes_key"),
        CheckConstraint("length(cuisine) > 0", name="ck_catalog_recipes_cuisine"),
        Index("idx_catalog_recipes_cuisine_active", "cuisine", "is_active"),
    )


class CatalogRecipeVersionORM(Base):
    """Immutable publishable recipe version."""

    __tablename__ = "catalog_recipe_versions"

    id = Column(String(36), primary_key=True, default=_uuid)
    recipe_id = Column(
        String(36),
        ForeignKey("catalog_recipes.id", ondelete="CASCADE"),
        nullable=False,
    )
    release_id = Column(
        String(36),
        ForeignKey("catalog_releases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    name = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    instructions = Column(JSON, nullable=False, default=list)
    prep_minutes = Column(Integer, nullable=True)
    cook_minutes = Column(Integer, nullable=True)
    servings = Column(Integer, nullable=False, default=1)
    calories = Column(Integer, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    fiber_g = Column(Float, nullable=False, default=0)
    sugar_g = Column(Float, nullable=False, default=0)
    source_revision = Column(String(120), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    recipe = relationship("CatalogRecipeORM", back_populates="versions", lazy="selectin")
    release = relationship("CatalogReleaseORM", back_populates="versions", lazy="selectin")
    meal_types = relationship(
        "CatalogRecipeMealTypeORM",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="CatalogRecipeMealTypeORM.meal_type",
        lazy="selectin",
    )
    ingredients = relationship(
        "CatalogRecipeIngredientORM",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="CatalogRecipeIngredientORM.position",
        lazy="selectin",
    )
    sources = relationship(
        "CatalogRecipeSourceORM",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    rights_records = relationship(
        "CatalogRecipeRightsRecordORM",
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "version_number",
            name="uq_catalog_recipe_versions_recipe_version",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name="ck_catalog_recipe_versions_status",
        ),
        CheckConstraint("version_number > 0", name="ck_catalog_versions_number"),
        CheckConstraint("servings > 0", name="ck_catalog_versions_servings"),
        CheckConstraint("calories >= 0", name="ck_catalog_versions_calories"),
        CheckConstraint(
            "protein_g >= 0 AND carbs_g >= 0 AND fat_g >= 0 "
            "AND fiber_g >= 0 AND sugar_g >= 0",
            name="ck_catalog_versions_macros_non_negative",
        ),
        CheckConstraint(
            "fiber_g <= carbs_g AND sugar_g <= carbs_g",
            name="ck_catalog_versions_fiber_sugar_bounds",
        ),
        Index("idx_catalog_recipe_versions_release_status", "release_id", "status"),
    )


class CatalogRecipeMealTypeORM(Base):
    """Meal type eligibility for a recipe version."""

    __tablename__ = "catalog_recipe_version_meal_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    meal_type = Column(String(30), nullable=False)

    version = relationship("CatalogRecipeVersionORM", back_populates="meal_types")

    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "meal_type",
            name="uq_catalog_recipe_meal_types_version_type",
        ),
        Index("idx_catalog_recipe_meal_types_type", "meal_type"),
    )


class CatalogRecipeIngredientORM(Base):
    """Immutable nutrition snapshot for one recipe ingredient."""

    __tablename__ = "catalog_recipe_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_reference_id = Column(
        Integer,
        ForeignKey("food_reference.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(80), nullable=False)
    resolved_grams = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    fiber_g = Column(Float, nullable=False, default=0)
    sugar_g = Column(Float, nullable=False, default=0)
    serving_snapshot = Column(JSON, nullable=True)
    source_revision = Column(String(120), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    is_display_only = Column(Boolean, nullable=False, default=False)

    version = relationship("CatalogRecipeVersionORM", back_populates="ingredients")

    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "position",
            name="uq_catalog_recipe_ingredients_version_position",
        ),
        CheckConstraint("quantity > 0", name="ck_catalog_ingredients_quantity"),
        CheckConstraint(
            "resolved_grams > 0",
            name="ck_catalog_ingredients_resolved_grams",
        ),
        CheckConstraint(
            "protein_g >= 0 AND carbs_g >= 0 AND fat_g >= 0 "
            "AND fiber_g >= 0 AND sugar_g >= 0",
            name="ck_catalog_ingredients_macros_non_negative",
        ),
        CheckConstraint(
            "fiber_g <= carbs_g AND sugar_g <= carbs_g",
            name="ck_catalog_ingredients_fiber_sugar_bounds",
        ),
        Index("idx_catalog_recipe_ingredients_food_ref", "food_reference_id"),
    )


class CatalogRecipeSourceORM(Base):
    """Source/provenance record for a recipe version."""

    __tablename__ = "catalog_recipe_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(40), nullable=False)
    source_url = Column(Text, nullable=True)
    attribution = Column(Text, nullable=True)
    license_name = Column(String(120), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    version = relationship("CatalogRecipeVersionORM", back_populates="sources")

    __table_args__ = (
        CheckConstraint("length(source_type) > 0", name="ck_catalog_sources_type"),
        Index("idx_catalog_recipe_sources_version", "version_id"),
    )


class CatalogRecipeRightsRecordORM(Base):
    """Approval record proving a version can be published."""

    __tablename__ = "catalog_recipe_rights_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(
        String(36),
        ForeignKey("catalog_recipe_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(20), nullable=False)
    approver = Column(String(255), nullable=False)
    agreement_identifier = Column(String(160), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    version = relationship("CatalogRecipeVersionORM", back_populates="rights_records")

    __table_args__ = (
        CheckConstraint(
            "status IN ('approved', 'pending', 'rejected')",
            name="ck_catalog_rights_status",
        ),
        Index("idx_catalog_recipe_rights_version_status", "version_id", "status"),
    )

