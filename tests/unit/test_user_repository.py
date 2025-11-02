"""
Unit tests for UserRepository.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.infra.database.config import Base
from src.infra.database.models.user.user import User
from src.infra.database.models.user.profile import UserProfile
from src.infra.repositories.user_repository import UserRepository


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def user_repository(db_session):
    """Create a UserRepository instance."""
    return UserRepository(db=db_session)


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        firebase_uid="firebase_123",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestUserRepository:
    """Test suite for UserRepository."""

    def test_create_user(self, user_repository):
        """Test creating a new user."""
        user = user_repository.create_user(
            email="newuser@example.com",
            username="newuser",
            password_hash="hashed_pwd"
        )
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.password_hash == "hashed_pwd"
        assert user.is_active is True

    def test_create_user_duplicate_email(self, user_repository, sample_user):
        """Test creating user with duplicate email raises error."""
        with pytest.raises(ValueError, match="User with this email or username already exists"):
            user_repository.create_user(
                email="test@example.com",
                username="different",
                password_hash="pwd"
            )

    def test_create_user_duplicate_username(self, user_repository, sample_user):
        """Test creating user with duplicate username raises error."""
        with pytest.raises(ValueError, match="User with this email or username already exists"):
            user_repository.create_user(
                email="different@example.com",
                username="testuser",
                password_hash="pwd"
            )

    def test_get_user_by_id(self, user_repository, sample_user):
        """Test retrieving user by ID."""
        user = user_repository.get_user_by_id(sample_user.id)
        
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == "test@example.com"

    def test_get_user_by_id_not_found(self, user_repository):
        """Test getting user with non-existent ID."""
        user = user_repository.get_user_by_id("non-existent-id")
        assert user is None

    def test_get_alias(self, user_repository, sample_user):
        """Test get() is alias for get_user_by_id()."""
        user = user_repository.get(sample_user.id)
        
        assert user is not None
        assert user.id == sample_user.id

    def test_get_user_by_email(self, user_repository, sample_user):
        """Test retrieving user by email."""
        user = user_repository.get_user_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    def test_get_user_by_email_not_found(self, user_repository):
        """Test getting user with non-existent email."""
        user = user_repository.get_user_by_email("nonexistent@example.com")
        assert user is None

    def test_get_user_by_username(self, user_repository, sample_user):
        """Test retrieving user by username."""
        user = user_repository.get_user_by_username("testuser")
        
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_get_user_by_username_not_found(self, user_repository):
        """Test getting user with non-existent username."""
        user = user_repository.get_user_by_username("nonexistent")
        assert user is None

    def test_get_user_by_firebase_uid(self, user_repository, sample_user):
        """Test retrieving user by Firebase UID."""
        user = user_repository.get_user_by_firebase_uid("firebase_123")
        
        assert user is not None
        assert user.firebase_uid == "firebase_123"
        assert user.email == "test@example.com"

    def test_get_user_by_firebase_uid_not_found(self, user_repository):
        """Test getting user with non-existent Firebase UID."""
        user = user_repository.get_user_by_firebase_uid("nonexistent_uid")
        assert user is None

    def test_create_user_profile(self, user_repository, sample_user):
        """Test creating a user profile."""
        profile = user_repository.create_user_profile(
            user_id=sample_user.id,
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=75.0,
            body_fat_percentage=15.0,
            activity_level="moderately_active",
            fitness_goal="maintenance",
            target_weight_kg=75.0,
            meals_per_day=3,
            snacks_per_day=1,
            dietary_preferences=["vegetarian"],
            health_conditions=["none"],
            allergies=["nuts"]
        )
        
        assert profile.id is not None
        assert profile.user_id == sample_user.id
        assert profile.age == 30
        assert profile.gender == "male"
        assert profile.height_cm == 175.0
        assert profile.weight_kg == 75.0
        assert profile.body_fat_percentage == 15.0
        assert profile.is_current is True
        assert profile.activity_level == "moderately_active"
        assert profile.fitness_goal == "maintenance"
        assert profile.meals_per_day == 3
        assert profile.snacks_per_day == 1
        assert profile.dietary_preferences == ["vegetarian"]
        assert profile.health_conditions == ["none"]
        assert profile.allergies == ["nuts"]

    def test_create_user_profile_marks_previous_as_not_current(self, user_repository, sample_user):
        """Test that creating new profile marks previous profiles as not current."""
        # Create first profile
        profile1 = user_repository.create_user_profile(
            user_id=sample_user.id,
            age=30,
            gender="male",
            height_cm=175.0,
            weight_kg=75.0
        )
        
        assert profile1.is_current is True
        
        # Create second profile
        profile2 = user_repository.create_user_profile(
            user_id=sample_user.id,
            age=31,
            gender="male",
            height_cm=175.0,
            weight_kg=73.0
        )
        
        # Refresh first profile
        user_repository.db.refresh(profile1)
        
        assert profile1.is_current is False
        assert profile2.is_current is True

    def test_get_current_user_profile(self, user_repository, sample_user):
        """Test retrieving current user profile."""
        # Create profile
        created_profile = user_repository.create_user_profile(
            user_id=sample_user.id,
            age=25,
            gender="female",
            height_cm=165.0,
            weight_kg=60.0
        )
        
        # Get current profile
        profile = user_repository.get_current_user_profile(sample_user.id)
        
        assert profile is not None
        assert profile.id == created_profile.id
        assert profile.is_current is True
        assert profile.age == 25

    def test_get_current_user_profile_not_found(self, user_repository, sample_user):
        """Test getting current profile when none exists."""
        profile = user_repository.get_current_user_profile(sample_user.id)
        assert profile is None

    def test_update_user_preferences(self, user_repository, sample_user):
        """Test updating user preferences."""
        # Create profile
        profile = user_repository.create_user_profile(
            user_id=sample_user.id,
            age=28,
            gender="female",
            height_cm=160.0,
            weight_kg=55.0,
            dietary_preferences=["vegan"],
            health_conditions=[],
            allergies=[]
        )
        
        # Update preferences
        updated_profile = user_repository.update_user_preferences(
            user_id=sample_user.id,
            dietary_preferences=["vegan", "gluten_free"],
            health_conditions=["diabetes"],
            allergies=["shellfish"]
        )
        
        assert updated_profile is not None
        assert updated_profile.dietary_preferences == ["vegan", "gluten_free"]
        assert updated_profile.health_conditions == ["diabetes"]
        assert updated_profile.allergies == ["shellfish"]

    def test_update_user_preferences_partial(self, user_repository, sample_user):
        """Test updating only some preferences."""
        # Create profile
        user_repository.create_user_profile(
            user_id=sample_user.id,
            age=30,
            gender="male",
            height_cm=180.0,
            weight_kg=80.0,
            dietary_preferences=["vegetarian"],
            health_conditions=[],
            allergies=["peanuts"]
        )
        
        # Update only dietary preferences
        updated_profile = user_repository.update_user_preferences(
            user_id=sample_user.id,
            dietary_preferences=["vegan"]
        )
        
        assert updated_profile.dietary_preferences == ["vegan"]
        assert updated_profile.allergies == ["peanuts"]  # Unchanged

    def test_update_user_preferences_no_profile(self, user_repository, sample_user):
        """Test updating preferences when no profile exists."""
        result = user_repository.update_user_preferences(
            user_id=sample_user.id,
            dietary_preferences=["vegan"]
        )
        assert result is None

    def test_update_user_goals(self, user_repository, sample_user):
        """Test updating user goals."""
        # Create profile
        profile = user_repository.create_user_profile(
            user_id=sample_user.id,
            age=35,
            gender="male",
            height_cm=178.0,
            weight_kg=85.0,
            activity_level="sedentary",
            fitness_goal="maintenance",
            target_weight_kg=85.0,
            meals_per_day=3,
            snacks_per_day=1
        )
        
        # Update goals
        updated_profile = user_repository.update_user_goals(
            user_id=sample_user.id,
            activity_level="very_active",
            fitness_goal="bulking",
            target_weight_kg=90.0,
            meals_per_day=4,
            snacks_per_day=2
        )
        
        assert updated_profile is not None
        assert updated_profile.activity_level == "very_active"
        assert updated_profile.fitness_goal == "bulking"
        assert updated_profile.target_weight_kg == 90.0
        assert updated_profile.meals_per_day == 4
        assert updated_profile.snacks_per_day == 2

    def test_update_user_goals_partial(self, user_repository, sample_user):
        """Test updating only some goals."""
        # Create profile
        user_repository.create_user_profile(
            user_id=sample_user.id,
            age=27,
            gender="female",
            height_cm=168.0,
            weight_kg=62.0,
            activity_level="lightly_active",
            fitness_goal="cutting",
            target_weight_kg=58.0
        )
        
        # Update only fitness goal
        updated_profile = user_repository.update_user_goals(
            user_id=sample_user.id,
            fitness_goal="maintenance"
        )
        
        assert updated_profile.fitness_goal == "maintenance"
        assert updated_profile.activity_level == "lightly_active"  # Unchanged

    def test_update_user_goals_no_profile(self, user_repository, sample_user):
        """Test updating goals when no profile exists."""
        result = user_repository.update_user_goals(
            user_id=sample_user.id,
            fitness_goal="bulking"
        )
        assert result is None

    def test_create_user_profile_with_defaults(self, user_repository, sample_user):
        """Test creating profile with default values."""
        profile = user_repository.create_user_profile(
            user_id=sample_user.id,
            age=40,
            gender="male",
            height_cm=172.0,
            weight_kg=78.0
        )
        
        assert profile.activity_level == "sedentary"
        assert profile.fitness_goal == "maintenance"
        assert profile.meals_per_day == 3
        assert profile.snacks_per_day == 1
        assert profile.dietary_preferences == []
        assert profile.health_conditions == []
        assert profile.allergies == []
        assert profile.body_fat_percentage is None
        assert profile.target_weight_kg is None

