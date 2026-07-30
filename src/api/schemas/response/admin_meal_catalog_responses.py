"""Requests and responses for admin meal catalog operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminMealCatalogImportRequest(BaseModel):
    """Manifest and resolver options shared by import and preview endpoints."""

    manifest: dict[str, Any]
    dry_run: bool = False
    partial: bool = False
    skip_exact_cuisine_count: bool = False
    expected_recipe_count: int = Field(default=180, ge=0)
    min_per_cuisine_meal_type: int = Field(default=5, ge=0)
    resolver_map: dict[str, int] = Field(default_factory=dict)
    auto_resolve_threshold: float | None = Field(default=0.92, ge=0, le=1)
    resolve_all_best_effort: bool = False


class AdminMealCatalogIngredientResponse(BaseModel):
    display_name: str
    quantity: float
    unit: str


class AdminMealCatalogItemResponse(BaseModel):
    id: str
    catalog_key: str
    name: str
    cuisine: str
    description: str | None = None
    image_url: str | None = None
    meal_types: list[str]
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    ingredient_count: int
    ingredients: list[AdminMealCatalogIngredientResponse]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminMealCatalogListResponse(BaseModel):
    items: list[AdminMealCatalogItemResponse]
    total: int
    limit: int
    offset: int


class AdminMealCatalogGenerateImageResponse(BaseModel):
    item: AdminMealCatalogItemResponse
    image_url: str


class AdminMealCatalogResolutionCandidate(BaseModel):
    food_reference_id: int
    name: str
    name_normalized: str | None = None
    source: str
    is_verified: bool
    score: float


class AdminMealCatalogResolutionIssue(BaseModel):
    recipe_index: int
    recipe_key: str
    ingredient_index: int
    ingredient_name: str
    normalized_name: str
    reason: str
    candidates: list[AdminMealCatalogResolutionCandidate]


class AdminMealCatalogUnverifiedReference(BaseModel):
    recipe_index: int
    recipe_key: str
    ingredient_index: int
    ingredient_name: str
    food_reference_id: int
    food_reference_name: str
    source: str


class AdminMealCatalogReviewRequired(BaseModel):
    recipe_index: int
    recipe_key: str
    reason: str
    matched_catalog_key: str
    ingredient_jaccard: float


class AdminMealCatalogValidationResponse(BaseModel):
    manifest_digest: str
    recipe_count: int
    errors: list[str]
    coverage: dict[str, dict[str, int]]


class AdminMealCatalogEnrichmentResponse(BaseModel):
    validation: AdminMealCatalogValidationResponse
    attempted: int
    enriched: int
    skipped_existing: int


class AdminMealCatalogApproveFoodReferenceRequest(BaseModel):
    """One food reference an administrator reviewed before catalog publication."""

    food_reference_id: int = Field(gt=0)


class AdminMealCatalogApproveFoodReferenceResponse(BaseModel):
    food_reference_id: int
    name: str
    source: str
    is_verified: bool


class AdminMealCatalogImportResponse(BaseModel):
    validation: AdminMealCatalogValidationResponse
    manifest_digest: str
    recipe_count: int
    coverage: dict[str, dict[str, int]]
    inserted: int
    skipped_existing: int
    dry_run: bool
    applied: bool
    errors: list[str]
    issues: list[AdminMealCatalogResolutionIssue]
    unverified_references: list[AdminMealCatalogUnverifiedReference]
    review_required: list[AdminMealCatalogReviewRequired]
