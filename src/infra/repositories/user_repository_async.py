"""Async user repository backed by asyncpg + AsyncSession."""
import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.model.user import UserDomainModel, UserProfileDomainModel
from src.domain.ports.user_repository_port import UserRepositoryPort
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User
from src.infra.mappers.user_mapper import UserMapper, UserProfileMapper

logger = logging.getLogger(__name__)

_USER_LOADS = (
    selectinload(User.profiles),
    selectinload(User.subscriptions),
)


class AsyncUserRepository(UserRepositoryPort):
    """Async SQLAlchemy user repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user_domain: UserDomainModel) -> UserDomainModel:
        user_entity = UserMapper.to_persistence(user_domain)
        user_entity.profiles = [UserProfileMapper.to_persistence(p) for p in user_domain.profiles]
        if not user_entity.id:
            self.session.add(user_entity)
        else:
            user_entity = await self.session.merge(user_entity)
        try:
            await self.session.flush()
            # Re-fetch with eager loading to satisfy lazy="raise" on profiles/subscriptions
            user_id_str = str(user_entity.id)
            result = await self.session.execute(
                select(User).options(*_USER_LOADS).where(User.id == user_id_str)
            )
            user_entity = result.scalars().first()
            return UserMapper.to_domain(user_entity)
        except IntegrityError as e:
            # Do NOT call session.rollback() — UoW.__aexit__ handles rollback
            error_msg = str(e.orig).lower() if e.orig else str(e).lower()
            if "email" in error_msg:
                raise ValueError("User with this email already exists")
            elif "firebase_uid" in error_msg:
                raise ValueError("Firebase UID already registered")
            else:
                raise ValueError("User with this email or username already exists")

    async def find_by_id(self, user_id: UUID) -> Optional[UserDomainModel]:
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        result = await self.session.execute(
            select(User).options(*_USER_LOADS)
            .where(User.id == user_id_str, User.is_active == True)
        )
        entity = result.scalars().first()
        return UserMapper.to_domain(entity) if entity else None

    async def find_by_email(self, email: str) -> Optional[UserDomainModel]:
        result = await self.session.execute(
            select(User).options(*_USER_LOADS)
            .where(User.email == email, User.is_active == True)
        )
        entity = result.scalars().first()
        return UserMapper.to_domain(entity) if entity else None

    async def find_by_firebase_uid(self, firebase_uid: str) -> Optional[UserDomainModel]:
        result = await self.session.execute(
            select(User).options(*_USER_LOADS)
            .where(User.firebase_uid == firebase_uid, User.is_active == True)
        )
        entity = result.scalars().first()
        return UserMapper.to_domain(entity) if entity else None

    async def find_deleted_by_firebase_uid(self, firebase_uid: str) -> Optional[UserDomainModel]:
        result = await self.session.execute(
            select(User).options(*_USER_LOADS)
            .where(User.firebase_uid == firebase_uid, User.is_active == False)
        )
        entity = result.scalars().first()
        return UserMapper.to_domain(entity) if entity else None

    async def find_all(self, limit: int = 100, offset: int = 0) -> List[UserDomainModel]:
        result = await self.session.execute(
            select(User).options(*_USER_LOADS)
            .where(User.is_active == True)
            .limit(limit).offset(offset)
        )
        return [UserMapper.to_domain(u) for u in result.scalars().all()]

    async def delete(self, user_id: UUID) -> bool:
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        result = await self.session.execute(
            select(User).where(User.id == user_id_str)
        )
        entity = result.scalars().first()
        if entity:
            entity.is_active = False
            await self.session.flush()
            return True
        return False

    async def get_profile(self, user_id: UUID) -> Optional[UserProfileDomainModel]:
        user_id_str = str(user_id) if isinstance(user_id, UUID) else user_id
        result = await self.session.execute(
            select(UserProfile)
            .where(UserProfile.user_id == user_id_str, UserProfile.is_current == True)
        )
        entity = result.scalars().first()
        return UserProfileMapper.to_domain(entity) if entity else None

    async def update_profile(self, profile_domain: UserProfileDomainModel) -> UserProfileDomainModel:
        profile_id_str = str(profile_domain.id) if isinstance(profile_domain.id, UUID) else profile_domain.id
        entity = await self.session.get(UserProfile, profile_id_str)
        if not entity:
            entity = UserProfileMapper.to_persistence(profile_domain)
            self.session.add(entity)
        else:
            for key, value in profile_domain.__dict__.items():
                if hasattr(entity, key) and key != "_sa_instance_state":
                    setattr(entity, key, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return UserProfileMapper.to_domain(entity)

    async def update_user_timezone(self, user_id: UUID, timezone: str) -> None:
        await self.session.execute(
            update(User).where(User.id == str(user_id)).values(timezone=timezone)
        )

    async def get_user_timezone(self, user_id: UUID) -> Optional[str]:
        result = await self.session.execute(
            select(User.timezone).where(User.id == str(user_id), User.is_active == True)
        )
        return result.scalar_one_or_none()

    async def update_user_language(self, user_id: UUID, language_code: str) -> None:
        await self.session.execute(
            update(User).where(User.id == str(user_id)).values(language_code=language_code)
        )
