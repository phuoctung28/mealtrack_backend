"""FastAPI dependency for GuestParseQuotaService (Postgres-backed)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services.guest_parse_quota import GuestParseQuotaService
from src.infra.config.settings import settings
from src.infra.database.config_async import get_async_db


def get_guest_quota_service(
    db: AsyncSession = Depends(get_async_db),
) -> GuestParseQuotaService:
    """Dependency that provides GuestParseQuotaService backed by Postgres."""
    return GuestParseQuotaService(db, hash_secret=settings.GUEST_INSTALL_HASH_SECRET)
