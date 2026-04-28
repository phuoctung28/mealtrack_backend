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
            job_type=profile_entity.job_type,
            training_days_per_week=profile_entity.training_days_per_week,
            training_minutes_per_session=profile_entity.training_minutes_per_session,
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
            training_level=profile_entity.training_level,
            date_of_birth=profile_entity.date_of_birth,
            referral_sources=profile_entity.referral_sources or [],
            challenge_duration=profile_entity.challenge_duration,
            training_types=profile_entity.training_types,
            custom_protein_g=profile_entity.custom_protein_g,
            custom_carbs_g=profile_entity.custom_carbs_g,
            custom_fat_g=profile_entity.custom_fat_g,
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
            job_type=profile_domain.job_type,
            training_days_per_week=profile_domain.training_days_per_week,
            training_minutes_per_session=profile_domain.training_minutes_per_session,
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
            training_level=profile_domain.training_level,
            date_of_birth=profile_domain.date_of_birth,
            referral_sources=profile_domain.referral_sources or [],
            challenge_duration=profile_domain.challenge_duration,
            training_types=profile_domain.training_types,
            custom_protein_g=profile_domain.custom_protein_g,
            custom_carbs_g=profile_domain.custom_carbs_g,
            custom_fat_g=profile_domain.custom_fat_g,
        )
