"""
Feature flags API endpoints for application-level feature control.
"""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.base_dependencies import get_cache_service
from src.api.dependencies.auth import require_admin
from src.api.schemas.request.feature_flag_requests import (
    CreateFeatureFlagRequest,
    UpdateFeatureFlagRequest,
)
from src.api.schemas.response.feature_flag_responses import (
    FeatureFlagCreatedResponse,
    FeatureFlagsResponse,
    FeatureFlagUpdatedResponse,
    IndividualFeatureFlagResponse,
)
from src.domain.cache.cache_keys import CacheKeys
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.config_async import get_async_db
from src.infra.database.models.feature_flag import FeatureFlag

router = APIRouter(prefix="/v1/feature-flags", tags=["Feature Flags"])


@router.get("/", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    db: AsyncSession = Depends(get_async_db),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """
    Get all feature flags from the database.

    Returns all feature flags currently stored in the system.
    """
    cache_key, ttl = CacheKeys.feature_flags()
    if cache_service:
        cached = await cache_service.get_json(cache_key)
        if cached:
            return FeatureFlagsResponse(**cached)

    result = await db.execute(select(FeatureFlag))
    feature_flags = result.scalars().all()
    flags_dict = {flag.name: flag.enabled for flag in feature_flags}

    response = FeatureFlagsResponse(flags=flags_dict, updated_at=utc_now())

    if cache_service:
        await cache_service.set_json(cache_key, response.model_dump(), ttl)

    return response


@router.get("/{feature_name}", response_model=IndividualFeatureFlagResponse)
async def get_individual_feature_flag(
    feature_name: str,
    db: AsyncSession = Depends(get_async_db),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """
    Get a specific feature flag from the database.

    - **feature_name**: Name of the feature flag to retrieve

    Returns the status of a single feature flag.
    """
    cache_key, ttl = CacheKeys.feature_flag(feature_name)
    if cache_service:
        cached = await cache_service.get_json(cache_key)
        if cached:
            return IndividualFeatureFlagResponse(**cached)

    result = await db.execute(select(FeatureFlag).where(FeatureFlag.name == feature_name))
    feature_flag = result.scalar_one_or_none()

    if not feature_flag:
        raise HTTPException(
            status_code=404, detail=f"Feature flag '{feature_name}' not found"
        )

    response = IndividualFeatureFlagResponse(
        name=feature_flag.name,
        enabled=feature_flag.enabled,
        description=feature_flag.description,
        created_at=feature_flag.created_at,
        updated_at=feature_flag.updated_at,
    )

    if cache_service:
        await cache_service.set_json(cache_key, response.model_dump(), ttl)

    return response


@router.post("/", response_model=FeatureFlagCreatedResponse, status_code=201)
async def create_feature_flag(
    request: CreateFeatureFlagRequest,
    db: AsyncSession = Depends(get_async_db),
    cache_service: CacheService | None = Depends(get_cache_service),
    _admin: str = Depends(require_admin),
):
    """
    Create a new feature flag.

    - **name**: Unique name for the feature flag
    - **enabled**: Initial enabled state (default: False)
    - **description**: Optional description of the feature flag

    Returns the created feature flag information.
    """
    # Check if feature flag already exists
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.name == request.name))
    existing_flag = result.scalar_one_or_none()
    if existing_flag:
        raise HTTPException(
            status_code=409, detail=f"Feature flag '{request.name}' already exists"
        )

    # Create new feature flag
    new_flag = FeatureFlag(
        name=request.name, enabled=request.enabled, description=request.description
    )

    db.add(new_flag)
    await db.commit()
    await db.refresh(new_flag)

    response = FeatureFlagCreatedResponse(
        name=new_flag.name,
        enabled=new_flag.enabled,
        description=new_flag.description,
        created_at=new_flag.created_at,
    )

    if cache_service:
        await cache_service.invalidate(CacheKeys.feature_flags()[0])
        await cache_service.invalidate(CacheKeys.feature_flag(new_flag.name)[0])

    return response


@router.put("/{feature_name}", response_model=FeatureFlagUpdatedResponse)
async def update_feature_flag(
    feature_name: str,
    request: UpdateFeatureFlagRequest,
    db: AsyncSession = Depends(get_async_db),
    cache_service: CacheService | None = Depends(get_cache_service),
    _admin: str = Depends(require_admin),
):
    """
    Update an existing feature flag.

    - **feature_name**: Name of the feature flag to update
    - **enabled**: New enabled state (optional)
    - **description**: New description (optional)

    Returns the updated feature flag information.
    """
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.name == feature_name))
    feature_flag = result.scalar_one_or_none()

    if not feature_flag:
        raise HTTPException(
            status_code=404, detail=f"Feature flag '{feature_name}' not found"
        )

    # Update only provided fields
    if request.enabled is not None:
        feature_flag.enabled = request.enabled
    if request.description is not None:
        feature_flag.description = request.description

    feature_flag.updated_at = utc_now()

    await db.commit()
    await db.refresh(feature_flag)

    response = FeatureFlagUpdatedResponse(
        name=feature_flag.name,
        enabled=feature_flag.enabled,
        description=feature_flag.description,
        updated_at=feature_flag.updated_at,
    )

    if cache_service:
        await cache_service.invalidate(CacheKeys.feature_flags()[0])
        await cache_service.invalidate(CacheKeys.feature_flag(feature_flag.name)[0])

    return response
