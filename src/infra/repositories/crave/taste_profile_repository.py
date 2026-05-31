from sqlalchemy.orm import Session

from src.infra.database.models.crave.user_taste_profile_model import UserTasteProfile


class TasteProfileRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_or_create(self, user_id: str) -> UserTasteProfile:
        profile = self._session.get(UserTasteProfile, user_id)
        if profile is None:
            profile = UserTasteProfile(user_id=user_id)
            self._session.add(profile)
        return profile

    def save(self, profile: UserTasteProfile) -> None:
        self._session.add(profile)
