"""Mappers for converting between domain models and persistence models."""
from src.domain.model.user import UserDomainModel, UserProfileDomainModel
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.user import User


class UserMapper:
    """Handles mapping between User domain and persistence models."""

    @staticmethod
    def to_domain(user_entity: User) -> UserDomainModel:
        """Map a User persistence entity to a UserDomainModel."""
        return UserDomainModel(
            id=user_entity.id,
            firebase_uid=user_entity.firebase_uid,
            email=user_entity.email,
            username=user_entity.username,
            password_hash=user_entity.password_hash,
            provider=user_entity.provider,
            is_active=user_entity.is_active,
            onboarding_completed=user_entity.onboarding_completed,
            last_accessed=user_entity.last_accessed,
            timezone=user_entity.timezone,
            first_name=user_entity.first_name,
            last_name=user_entity.last_name,
            phone_number=user_entity.phone_number,
            display_name=user_entity.display_name,
            photo_url=user_entity.photo_url,
            deleted_at=user_entity.deleted_at,
            created_at=user_entity.created_at,
            updated_at=user_entity.updated_at,
            profiles=[UserProfileMapper.to_domain(p) for p in user_entity.profiles],
        )

    @staticmethod
    def to_persistence(user_domain: UserDomainModel) -> User:
        """Map a UserDomainModel to a User persistence entity."""
        return User(
            id=str(user_domain.id) if user_domain.id else None,
            firebase_uid=user_domain.firebase_uid,
            email=user_domain.email,
            username=user_domain.username,
            password_hash=user_domain.password_hash,
            provider=user_domain.provider,
            is_active=user_domain.is_active,
            onboarding_completed=user_domain.onboarding_completed,
            last_accessed=user_domain.last_accessed,
            timezone=user_domain.timezone,
            first_name=user_domain.first_name,
            last_name=user_domain.last_name,
            phone_number=user_domain.phone_number,
            display_name=user_domain.display_name,
            photo_url=user_domain.photo_url,
            deleted_at=user_domain.deleted_at,
        )


class UserProfileMapper:
    """Handles mapping between UserProfile domain and persistence models."""

    @staticmethod
    def to_domain(profile_entity: UserProfile) -> UserProfileDomainModel:
        """Map a UserProfile persistence entity to a UserProfileDomainModel."""
        return UserProfileDomainModel(
            id=profile_entity.id,
            user_id=profile_entity.user_id,
            age=profile_entity.age,
            gender=profile_entity.gender,
            height_cm=profile_entity.height_cm,
            weight_kg=profile_entity.weight_kg,
            activity_level=profile_entity.activity_level,
            fitness_goal=profile_entity.fitness_goal,
            meals_per_day=profile_entity.meals_per_day,
            is_current=profile_entity.is_current,
            body_fat_percentage=profile_entity.body_fat_percentage,
            target_weight_kg=profile_entity.target_weight_kg,
            snacks_per_day=profile_entity.snacks_per_day,
            dietary_preferences=profile_entity.dietary_preferences,
            health_conditions=profile_entity.health_conditions,
            allergies=profile_entity.allergies,
            pain_points=profile_entity.pain_points,
            created_at=profile_entity.created_at,
            updated_at=profile_entity.updated_at,
        )

    @staticmethod
    def to_persistence(profile_domain: UserProfileDomainModel) -> UserProfile:
        """Map a UserProfileDomainModel to a UserProfile persistence entity."""
        return UserProfile(
            id=str(profile_domain.id) if profile_domain.id else None,
            user_id=str(profile_domain.user_id) if profile_domain.user_id else None,
            age=profile_domain.age,
            gender=profile_domain.gender,
            height_cm=profile_domain.height_cm,
            weight_kg=profile_domain.weight_kg,
            activity_level=profile_domain.activity_level,
            fitness_goal=profile_domain.fitness_goal,
            meals_per_day=profile_domain.meals_per_day,
            is_current=profile_domain.is_current,
            body_fat_percentage=profile_domain.body_fat_percentage,
            target_weight_kg=profile_domain.target_weight_kg,
            snacks_per_day=profile_domain.snacks_per_day,
            dietary_preferences=profile_domain.dietary_preferences,
            health_conditions=profile_domain.health_conditions,
            allergies=profile_domain.allergies,
            pain_points=profile_domain.pain_points,
        )
