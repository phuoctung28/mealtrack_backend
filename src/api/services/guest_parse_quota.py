"""Guest parse quota enforcement using PostgreSQL for one-shot AI trial protection."""
import hashlib
import hmac
import logging
import re
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.ai_handshake_guest_trial_quota import (
    AiHandshakeGuestTrialQuota,
)

logger = logging.getLogger(__name__)

_INSTALL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{8,128}$")
_RESERVE_TTL = 30  # seconds — in-flight guard window


class GuestParseQuotaError(Exception):
    pass


class QuotaAlreadyUsedError(GuestParseQuotaError):
    pass


class QuotaUnavailableError(GuestParseQuotaError):
    pass


class QuotaInFlightError(GuestParseQuotaError):
    """Another request from same install id is already in flight."""
    pass


def validate_install_id(install_id: str) -> bool:
    return bool(_INSTALL_ID_PATTERN.match(install_id))


def _hash_install_id(install_id: str, secret: str) -> str:
    return hmac.new(
        secret.encode() if secret else b"dev-fallback-secret",
        install_id.encode(),
        hashlib.sha256,
    ).hexdigest()


class GuestParseQuotaService:
    def __init__(self, session: AsyncSession, hash_secret: str = ""):
        self._session = session
        self._secret = hash_secret

    async def reserve(self, install_id: str) -> str:
        """
        Atomically reserve a guest parse trial slot.

        Returns install_hash on success. Raises QuotaAlreadyUsedError,
        QuotaUnavailableError, or QuotaInFlightError.
        """
        id_hash = _hash_install_id(install_id, self._secret)
        now = utc_now()
        reserved_until = now + timedelta(seconds=_RESERVE_TTL)

        try:
            async with self._session.begin_nested():
                self._session.add(
                    AiHandshakeGuestTrialQuota(
                        install_hash=id_hash,
                        status="reserved",
                        reserved_until=reserved_until,
                        created_at=now,
                        updated_at=now,
                    )
                )
                await self._session.flush()
            # Insert succeeded — fresh trial slot claimed
            return id_hash

        except IntegrityError:
            # Row already exists; inspect its state under a row-level lock
            pass
        except SQLAlchemyError as exc:
            logger.error("quota_reserve_db_error hash_prefix=%s", id_hash[:8])
            raise QuotaUnavailableError("DB unavailable") from exc

        try:
            result = await self._session.execute(
                select(AiHandshakeGuestTrialQuota)
                .where(AiHandshakeGuestTrialQuota.install_hash == id_hash)
                .with_for_update()
            )
            row = result.scalar_one()
        except SQLAlchemyError as exc:
            logger.error("quota_reserve_select_error hash_prefix=%s", id_hash[:8])
            raise QuotaUnavailableError("DB unavailable") from exc

        if row.status == "completed":
            raise QuotaAlreadyUsedError

        if row.reserved_until is not None and row.reserved_until > utc_now():
            raise QuotaInFlightError

        # Expired reservation — reclaim it for this attempt
        try:
            row.status = "reserved"
            row.reserved_until = utc_now() + timedelta(seconds=_RESERVE_TTL)
            row.updated_at = utc_now()
            await self._session.flush()
        except SQLAlchemyError as exc:
            logger.error("quota_reserve_update_error hash_prefix=%s", id_hash[:8])
            raise QuotaUnavailableError("DB unavailable") from exc

        return id_hash

    async def mark_completed(self, id_hash: str) -> None:
        """Mark trial permanently consumed after a successful AI response."""
        try:
            result = await self._session.execute(
                select(AiHandshakeGuestTrialQuota)
                .where(AiHandshakeGuestTrialQuota.install_hash == id_hash)
                .with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None:
                logger.warning("quota_mark_completed_missing hash_prefix=%s", id_hash[:8])
                return
            now = utc_now()
            row.status = "completed"
            row.completed_at = now
            row.reserved_until = None
            row.updated_at = now
            await self._session.flush()
        except SQLAlchemyError as exc:
            logger.error("quota_mark_completed_error hash_prefix=%s", id_hash[:8])
            raise QuotaUnavailableError("DB unavailable") from exc

    async def release_reservation(self, id_hash: str) -> None:
        """Release in-flight reservation on AI failure so the user can retry."""
        try:
            result = await self._session.execute(
                select(AiHandshakeGuestTrialQuota)
                .where(AiHandshakeGuestTrialQuota.install_hash == id_hash)
                .with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None or row.status == "completed":
                # Never delete completed rows
                return
            await self._session.delete(row)
            await self._session.flush()
        except SQLAlchemyError:
            # Best-effort release; log but don't propagate so the original error surfaces
            logger.warning("quota_release_error hash_prefix=%s", id_hash[:8])
