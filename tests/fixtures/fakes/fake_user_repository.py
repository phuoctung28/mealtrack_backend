from typing import List, Optional
from uuid import UUID

from src.domain.model.user import UserDomainModel, UserProfileDomainModel
from src.domain.ports.user_repository_port import UserRepositoryPort


class FakeUserRepository(UserRepositoryPort):
    def __init__(self):
        self.users = {}  # id -> user
        self.profiles = {} # user_id -> profile

    def save(self, user: UserDomainModel) -> UserDomainModel:
        self.users[user.id] = user
        return user

    def find_by_id(self, user_id: UUID) -> Optional[UserDomainModel]:
        return self.users.get(user_id)

    def find_by_firebase_uid(self, firebase_uid: str) -> Optional[UserDomainModel]:
        for user in self.users.values():
            if user.firebase_uid == firebase_uid:
                return user
        return None

    def find_by_email(self, email: str) -> Optional[UserDomainModel]:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def find_all(self, limit: int = 100, offset: int = 0) -> List[UserDomainModel]:
        return list(self.users.values())[offset : offset + limit]

    def delete(self, user_id: UUID) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False

    def get_profile(self, user_id: UUID) -> Optional[UserProfileDomainModel]:
        return self.profiles.get(user_id)

    def update_profile(self, profile: UserProfileDomainModel) -> UserProfileDomainModel:
        self.profiles[profile.user_id] = profile
        return profile
