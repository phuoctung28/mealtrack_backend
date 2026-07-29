"""Protected admin endpoints for importing the curated meal catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.base_dependencies import get_async_db
from src.api.dependencies.auth import require_admin_or_local
from src.api.schemas.response.admin_meal_catalog_responses import (
    AdminMealCatalogImportRequest,
    AdminMealCatalogImportResponse,
    AdminMealCatalogValidationResponse,
)
from src.app.services.catalog_meal_seed_import_service import CatalogMealSeedImporter
from src.domain.services.meal_recommendation.catalog_recipe_seed_validator import (
    PRODUCTION_CUISINE_COUNTS,
    validate_catalog_seed_manifest,
)
from src.infra.repositories.catalog_recipe_repository_async import (
    AsyncCatalogMealRepository,
)
from src.infra.repositories.food_reference_repository_async import (
    AsyncFoodReferenceRepository,
)

router = APIRouter(prefix="/v1/admin/meal-catalog", tags=["Admin Meal Catalog"])


@router.post("/resolve", response_model=AdminMealCatalogImportResponse)
async def resolve_admin_meal_catalog_ingredients(
    request: AdminMealCatalogImportRequest,
    db: AsyncSession = Depends(get_async_db),
    _admin: str = Depends(require_admin_or_local),
) -> AdminMealCatalogImportResponse:
    """Validate and resolve a manifest without changing the catalog."""

    validation = _validate_manifest(request)
    if validation.errors:
        return _response(
            validation, _empty_summary(validation, dry_run=True), applied=False
        )
    summary = await _run_importer(db, request, dry_run=True)
    return _response(validation, summary, applied=False)


@router.post("/import", response_model=AdminMealCatalogImportResponse)
async def import_admin_meal_catalog(
    request: AdminMealCatalogImportRequest,
    db: AsyncSession = Depends(get_async_db),
    _admin: str = Depends(require_admin_or_local),
) -> AdminMealCatalogImportResponse:
    """Import a validated manifest, or preview it when ``dry_run`` is true."""

    validation = _validate_manifest(request)
    if validation.errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_response(
                validation,
                _empty_summary(validation, dry_run=request.dry_run),
                applied=False,
            ).model_dump(),
        )

    preview = await _run_importer(db, request, dry_run=True)
    if not preview.is_successful or request.dry_run:
        return _response(validation, preview, applied=False)

    summary = await _run_importer(db, request, dry_run=False)
    if not summary.is_successful:
        await db.rollback()
        return _response(validation, summary, applied=False)
    await db.commit()
    return _response(validation, summary, applied=True)


def _validate_manifest(request: AdminMealCatalogImportRequest):
    recipes = request.manifest.get("recipes", [])
    if not isinstance(recipes, list):
        recipes = []
    expected_count = len(recipes) if request.partial else request.expected_recipe_count
    return validate_catalog_seed_manifest(
        request.manifest,
        expected_recipe_count=expected_count,
        min_per_cuisine_meal_type=request.min_per_cuisine_meal_type,
        expected_cuisine_counts=(
            None
            if request.partial or request.skip_exact_cuisine_count
            else PRODUCTION_CUISINE_COUNTS
        ),
        allow_declared_expected_count_mismatch=request.partial,
    )


async def _run_importer(
    db: AsyncSession,
    request: AdminMealCatalogImportRequest,
    *,
    dry_run: bool,
):
    return await CatalogMealSeedImporter(
        AsyncCatalogMealRepository(db),
        AsyncFoodReferenceRepository(db),
        dry_run=dry_run,
        approved_mappings=request.resolver_map,
        auto_resolve_threshold=(
            0.0
            if request.resolve_all_best_effort
            and request.auto_resolve_threshold is None
            else request.auto_resolve_threshold
        ),
        resolve_all_best_effort=request.resolve_all_best_effort,
    ).import_manifest(request.manifest)


def _empty_summary(validation, *, dry_run: bool):
    from src.app.services.catalog_meal_seed_import_service import (
        CatalogSeedImportSummary,
    )

    return CatalogSeedImportSummary(
        dry_run=dry_run,
        errors=tuple(validation.errors),
    )


def _response(validation, summary, *, applied: bool) -> AdminMealCatalogImportResponse:
    report = summary.resolution_report()
    validation_response = AdminMealCatalogValidationResponse(
        manifest_digest=validation.manifest_digest,
        recipe_count=validation.recipe_count,
        errors=list(validation.errors),
        coverage=validation.coverage,
    )
    return AdminMealCatalogImportResponse(
        validation=validation_response,
        manifest_digest=validation.manifest_digest,
        recipe_count=validation.recipe_count,
        coverage=validation.coverage,
        inserted=summary.inserted,
        skipped_existing=summary.skipped_existing,
        dry_run=summary.dry_run,
        applied=applied,
        errors=list(summary.errors),
        issues=report["issues"],
        review_required=report["review_required"],
    )
