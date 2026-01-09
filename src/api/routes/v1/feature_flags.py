"""
Feature flags API endpoints for application-level feature control.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.api.base_dependencies import get_cache_service, get_db
from src.api.schemas.request.feature_flag_requests import CreateFeatureFlagRequest, UpdateFeatureFlagRequest
from src.api.schemas.response.feature_flag_responses import (
    FeatureFlagsResponse,
    IndividualFeatureFlagResponse,
    FeatureFlagCreatedResponse,
    FeatureFlagUpdatedResponse
)
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.feature_flag import FeatureFlag

router = APIRouter(prefix="/v1/feature-flags", tags=["Feature Flags"])


@router.get("/", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    db: Session = Depends(get_db),
    cache_service: Optional[CacheService] = Depends(get_cache_service),
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

    feature_flags = db.query(FeatureFlag).all()
    flags_dict = {flag.name: flag.enabled for flag in feature_flags}

    response = FeatureFlagsResponse(
        flags=flags_dict,
        updated_at=datetime.utcnow()
    )

    if cache_service:
        await cache_service.set_json(cache_key, response.model_dump(), ttl)

    return response


@router.get("/{feature_name}", response_model=IndividualFeatureFlagResponse)
async def get_individual_feature_flag(
    feature_name: str,
    db: Session = Depends(get_db),
    cache_service: Optional[CacheService] = Depends(get_cache_service),
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

    feature_flag = db.query(FeatureFlag).filter(FeatureFlag.name == feature_name).first()
    
    if not feature_flag:
        raise HTTPException(
            status_code=404,
            detail=f"Feature flag '{feature_name}' not found"
        )
    
    response = IndividualFeatureFlagResponse(
        name=feature_flag.name,
        enabled=feature_flag.enabled,
        description=feature_flag.description,
        created_at=feature_flag.created_at,
        updated_at=feature_flag.updated_at
    )

    if cache_service:
        await cache_service.set_json(cache_key, response.model_dump(), ttl)

    return response


@router.post("/", response_model=FeatureFlagCreatedResponse, status_code=201)
async def create_feature_flag(
    request: CreateFeatureFlagRequest,
    db: Session = Depends(get_db),
    cache_service: Optional[CacheService] = Depends(get_cache_service),
):
    """
    Create a new feature flag.
    
    - **name**: Unique name for the feature flag
    - **enabled**: Initial enabled state (default: False)  
    - **description**: Optional description of the feature flag
    
    Returns the created feature flag information.
    """
    # Check if feature flag already exists
    existing_flag = db.query(FeatureFlag).filter(FeatureFlag.name == request.name).first()
    if existing_flag:
        raise HTTPException(
            status_code=409,
            detail=f"Feature flag '{request.name}' already exists"
        )
    
    # Create new feature flag
    new_flag = FeatureFlag(
        name=request.name,
        enabled=request.enabled,
        description=request.description
    )
    
    db.add(new_flag)
    db.commit()
    db.refresh(new_flag)
    
    response = FeatureFlagCreatedResponse(
        name=new_flag.name,
        enabled=new_flag.enabled,
        description=new_flag.description,
        created_at=new_flag.created_at
    )

    if cache_service:
        await cache_service.invalidate(CacheKeys.feature_flags()[0])
        await cache_service.invalidate(CacheKeys.feature_flag(new_flag.name)[0])

    return response


@router.put("/{feature_name}", response_model=FeatureFlagUpdatedResponse)
async def update_feature_flag(
    feature_name: str, 
    request: UpdateFeatureFlagRequest, 
    db: Session = Depends(get_db),
    cache_service: Optional[CacheService] = Depends(get_cache_service),
):
    """
    Update an existing feature flag.
    
    - **feature_name**: Name of the feature flag to update
    - **enabled**: New enabled state (optional)
    - **description**: New description (optional)
    
    Returns the updated feature flag information.
    """
    feature_flag = db.query(FeatureFlag).filter(FeatureFlag.name == feature_name).first()
    
    if not feature_flag:
        raise HTTPException(
            status_code=404,
            detail=f"Feature flag '{feature_name}' not found"
        )
    
    # Update only provided fields
    if request.enabled is not None:
        feature_flag.enabled = request.enabled
    if request.description is not None:
        feature_flag.description = request.description
    
    feature_flag.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(feature_flag)
    
    response = FeatureFlagUpdatedResponse(
        name=feature_flag.name,
        enabled=feature_flag.enabled,
        description=feature_flag.description,
        updated_at=feature_flag.updated_at
    )

    if cache_service:
        await cache_service.invalidate(CacheKeys.feature_flags()[0])
        await cache_service.invalidate(CacheKeys.feature_flag(feature_flag.name)[0])

    return response