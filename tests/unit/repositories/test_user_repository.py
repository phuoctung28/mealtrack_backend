"""
Unit tests for UserRepository.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from src.infra.database.config import Base
from src.infra.repositories.user_repository import UserRepository
from src.domain.model.user import UserDomainModel, UserProfileDomainModel
from src.api.schemas.common.auth_enums import AuthProviderEnum
from src.domain.model.auth.auth_provider import AuthProvider


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def user_repository(db_session):
    """Create a UserRepository instance."""
    return UserRepository(db=db_session)


@pytest.fixture
def sample_user(user_repository):
    """Create a sample user for testing."""
    user_domain = UserDomainModel(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        firebase_uid="firebase_123",
        provider=AuthProvider.GOOGLE,
        is_active=True
    )
    return user_repository.save(user_domain)


class TestUserRepository:
    """Test suite for UserRepository."""

    def test_save_new_user(self, user_repository):
        """Test creating a new user."""
        user_domain = UserDomainModel(
            id=uuid4(),
            email="newuser@example.com",
            username="newuser",
            password_hash="hashed_pwd",
            firebase_uid="firebase_newuser",
            provider=AuthProvider.GOOGLE
        )
        
        saved_user = user_repository.save(user_domain)
        
        assert saved_user.id is not None
        assert saved_user.email == "newuser@example.com"
        assert saved_user.username == "newuser"

    def test_find_by_id(self, user_repository, sample_user):
        """Test retrieving user by ID."""
        user = user_repository.find_by_id(sample_user.id)
        
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == "test@example.com"

    def test_find_by_id_not_found(self, user_repository):
        """Test getting user with non-existent ID."""
        user = user_repository.find_by_id(uuid4())
        assert user is None

    def test_find_by_email(self, user_repository, sample_user):
        """Test retrieving user by email."""
        user = user_repository.find_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"

    def test_find_by_email_not_found(self, user_repository):
        """Test getting user with non-existent email."""
        user = user_repository.find_by_email("nonexistent@example.com")
        assert user is None

    def test_update_profile(self, user_repository, sample_user):
        """Test updating user profile."""
        # Create initial profile via User entity (simplified for test)
        # In reality, profile creation logic might be more complex
        
        # Manually create profile domain object
        profile_domain = UserProfileDomainModel(
            user_id=sample_user.id,
            age=30,
            gender="male",
            height_cm=180,
            weight_kg=75,
            activity_level="active",
            fitness_goal="maintenance",
            meals_per_day=3,
            is_current=True
        )
        
        # Attach to user and save (to simulate profile creation)
        sample_user.profiles.append(profile_domain)
        user_repository.save(sample_user)
        
        # Now update it
        # Fetch fresh to get the profile ID
        user = user_repository.find_by_id(sample_user.id)
        profile = user.current_profile
        assert profile is not None
        
        profile.weight_kg = 70
        updated_profile = user_repository.update_profile(profile)
        
        assert updated_profile.weight_kg == 70
        assert updated_profile.id == profile.id

    def test_delete_user(self, user_repository, sample_user):
        """Test soft deleting a user."""
        result = user_repository.delete(sample_user.id)
        assert result is True
        
        # Verify user is not found (filtered out by is_active=True)
        user = user_repository.find_by_id(sample_user.id)
        assert user is None
