"""Feature flags API endpoints for application-level feature control."""

from fastapi import APIRouter, HTTPException, Depends

from src.api.dependencies.event_bus import get_event_bus
from src.api.schemas.request.feature_flag_requests import (
    CreateFeatureFlagRequest,
    UpdateFeatureFlagRequest,
)
from src.api.schemas.response.feature_flag_responses import (
    FeatureFlagsResponse,
    IndividualFeatureFlagResponse,
    FeatureFlagCreatedResponse,
    FeatureFlagUpdatedResponse,
)
from src.app.commands.feature_flag import CreateFeatureFlagCommand, UpdateFeatureFlagCommand
from src.app.handlers.command_handlers.feature_flag.create_feature_flag_handler import (
    FeatureFlagExistsError,
)
from src.app.handlers.command_handlers.feature_flag.update_feature_flag_handler import (
    FeatureFlagNotFoundError as UpdateNotFoundError,
)
from src.app.handlers.query_handlers.feature_flag.get_feature_flag_by_name_handler import (
    FeatureFlagNotFoundError,
)
from src.app.queries.feature_flag import GetFeatureFlagsQuery, GetFeatureFlagByNameQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/feature-flags", tags=["Feature Flags"])


@router.get("/", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    event_bus: EventBus = Depends(get_event_bus),
):
    """Get all feature flags from the database."""
    result = await event_bus.send(GetFeatureFlagsQuery())
    return FeatureFlagsResponse(flags=result.flags, updated_at=result.updated_at)


@router.get("/{feature_name}", response_model=IndividualFeatureFlagResponse)
async def get_individual_feature_flag(
    feature_name: str,
    event_bus: EventBus = Depends(get_event_bus),
):
    """Get a specific feature flag from the database."""
    try:
        result = await event_bus.send(GetFeatureFlagByNameQuery(name=feature_name))
    except FeatureFlagNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Feature flag '{feature_name}' not found"
        )

    return IndividualFeatureFlagResponse(
        name=result.name,
        enabled=result.enabled,
        description=result.description,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("/", response_model=FeatureFlagCreatedResponse, status_code=201)
async def create_feature_flag(
    request: CreateFeatureFlagRequest,
    event_bus: EventBus = Depends(get_event_bus),
):
    """Create a new feature flag."""
    try:
        result = await event_bus.send(
            CreateFeatureFlagCommand(
                name=request.name,
                enabled=request.enabled,
                description=request.description,
            )
        )
    except FeatureFlagExistsError:
        raise HTTPException(
            status_code=409, detail=f"Feature flag '{request.name}' already exists"
        )

    return FeatureFlagCreatedResponse(
        name=result.name,
        enabled=result.enabled,
        description=result.description,
        created_at=result.created_at,
    )


@router.put("/{feature_name}", response_model=FeatureFlagUpdatedResponse)
async def update_feature_flag(
    feature_name: str,
    request: UpdateFeatureFlagRequest,
    event_bus: EventBus = Depends(get_event_bus),
):
    """Update an existing feature flag."""
    try:
        result = await event_bus.send(
            UpdateFeatureFlagCommand(
                name=feature_name,
                enabled=request.enabled,
                description=request.description,
            )
        )
    except UpdateNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Feature flag '{feature_name}' not found"
        )

    return FeatureFlagUpdatedResponse(
        name=result.name,
        enabled=result.enabled,
        description=result.description,
        updated_at=result.updated_at,
    )
