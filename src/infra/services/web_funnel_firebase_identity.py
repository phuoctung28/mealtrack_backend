"""Narrow Firebase Admin boundary for paid web claim identity decisions."""

import asyncio
import hashlib
from dataclasses import dataclass

from firebase_admin import auth  # type: ignore[import-untyped]


class FirebaseIdentityConflict(Exception):
    """Raised without revealing the existing account's authentication method."""


@dataclass(frozen=True)
class FirebaseIdentity:
    uid: str
    email: str
    is_provisional: bool = False


class WebFunnelFirebaseIdentityService:
    """Create only verified email-only identities; never link/merge providers."""

    @staticmethod
    def _uid_for(lead_id: str) -> str:
        return f"wf_{hashlib.sha256(lead_id.encode()).hexdigest()[:40]}"

    async def resolve(self, lead_id: str, email: str) -> FirebaseIdentity:
        is_provisional = False
        try:
            record = await asyncio.to_thread(auth.get_user_by_email, email)
        except auth.UserNotFoundError:
            uid = self._uid_for(lead_id)
            try:
                record = await asyncio.to_thread(
                    auth.create_user, uid=uid, email=email, email_verified=True
                )
                is_provisional = True
            except auth.UidAlreadyExistsError:
                record = await asyncio.to_thread(auth.get_user, uid)
        if not record.email_verified or record.disabled:
            raise FirebaseIdentityConflict()
        providers = {item.provider_id for item in record.provider_data}
        if providers - {"password"}:
            raise FirebaseIdentityConflict()
        if (record.email or "").lower() != email.lower():
            raise FirebaseIdentityConflict()
        return FirebaseIdentity(
            uid=record.uid,
            email=email.lower(),
            is_provisional=is_provisional,
        )

    async def mint_custom_token(self, identity: FirebaseIdentity, reservation_id: str, generation: int) -> str:
        token = await asyncio.to_thread(
            auth.create_custom_token,
            identity.uid,
            {"wf_reservation": reservation_id, "wf_generation": generation},
        )
        return token.decode("utf-8") if isinstance(token, bytes) else token

    async def delete_unclaimed_provisional(self, uid: str) -> None:
        """Delete only deterministic web-funnel identities after an abandoned reservation."""
        if not uid.startswith("wf_"):
            raise FirebaseIdentityConflict()
        await asyncio.to_thread(auth.delete_user, uid)
