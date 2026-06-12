from uuid import uuid4

from src.domain.model.user import UserProfileDomainModel
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.models.user.profile_preference import UserProfilePreference
from src.infra.mappers.user_mapper import (
    UserProfileMapper,
    build_profile_preference_entries,
)
from src.infra.repositories.user_repository_async import (
    _sync_profile_preference_entries,
)


def _profile_entity(**overrides) -> UserProfile:
    values = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "age": 30,
        "gender": "female",
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "job_type": "desk",
        "training_days_per_week": 3,
        "training_minutes_per_session": 45,
        "fitness_goal": "maintenance",
        "meals_per_day": 3,
        "snacks_per_day": 1,
        "dietary_preferences": ["legacy"],
        "health_conditions": [],
        "allergies": [],
        "pain_points": [],
        "referral_sources": [],
        "training_types": [],
        "is_current": True,
    }
    values.update(overrides)
    return UserProfile(**values)


def test_mapper_prefers_normalized_profile_preferences() -> None:
    profile = _profile_entity(dietary_preferences=["legacy"])
    profile.preference_entries = [
        UserProfilePreference(
            preference_type="dietary_preferences",
            value="vegan",
            position=1,
        ),
        UserProfilePreference(
            preference_type="dietary_preferences",
            value="vegetarian",
            position=0,
        ),
    ]

    domain = UserProfileMapper.to_domain(profile)

    assert domain.dietary_preferences == ["vegetarian", "vegan"]


def test_mapper_falls_back_to_legacy_json_arrays() -> None:
    profile = _profile_entity(
        dietary_preferences=["vegetarian"],
        allergies=["peanuts"],
    )

    domain = UserProfileMapper.to_domain(profile)

    assert domain.dietary_preferences == ["vegetarian"]
    assert domain.allergies == ["peanuts"]


def test_profile_persistence_dual_writes_normalized_and_legacy_values() -> None:
    domain = UserProfileDomainModel(
        id=uuid4(),
        user_id=uuid4(),
        age=30,
        gender="female",
        height_cm=165.0,
        weight_kg=60.0,
        job_type="desk",
        training_days_per_week=3,
        training_minutes_per_session=45,
        fitness_goal="maintenance",
        meals_per_day=3,
        dietary_preferences=[" vegetarian ", "vegetarian", None, "vegan"],
        allergies=["peanuts"],
    )

    orm_profile = UserProfileMapper.to_persistence(domain)

    assert orm_profile.dietary_preferences == [
        " vegetarian ",
        "vegetarian",
        None,
        "vegan",
    ]
    assert [
        (entry.preference_type, entry.value, entry.position)
        for entry in orm_profile.preference_entries
    ] == [
        ("dietary_preferences", "vegetarian", 0),
        ("dietary_preferences", "vegan", 1),
        ("allergies", "peanuts", 0),
    ]


def test_build_profile_preference_entries_skips_empty_values() -> None:
    domain = UserProfileDomainModel(
        id=uuid4(),
        user_id=uuid4(),
        age=30,
        gender="female",
        height_cm=165.0,
        weight_kg=60.0,
        job_type="desk",
        training_days_per_week=3,
        training_minutes_per_session=45,
        fitness_goal="maintenance",
        meals_per_day=3,
        pain_points=["", "  ", "busy"],
    )

    entries = build_profile_preference_entries(domain)

    assert [(entry.preference_type, entry.value) for entry in entries] == [
        ("pain_points", "busy")
    ]


def test_sync_profile_preference_entries_reuses_matching_rows() -> None:
    profile_id = str(uuid4())
    existing_classic = UserProfilePreference(
        profile_id=profile_id,
        preference_type="dietary_preferences",
        value="classic",
        position=0,
    )
    stale_pain_point = UserProfilePreference(
        profile_id=profile_id,
        preference_type="pain_points",
        value="old",
        position=0,
    )
    profile = _profile_entity(id=profile_id)
    profile.preference_entries = [existing_classic, stale_pain_point]
    domain = UserProfileDomainModel(
        id=uuid4(),
        user_id=uuid4(),
        age=31,
        gender="female",
        height_cm=165,
        weight_kg=60,
        job_type="desk",
        training_days_per_week=3,
        training_minutes_per_session=45,
        fitness_goal="maintenance",
        meals_per_day=3,
        dietary_preferences=["classic"],
        pain_points=["new"],
    )

    _sync_profile_preference_entries(profile, domain)

    assert profile.preference_entries[0] is existing_classic
    assert [
        (entry.preference_type, entry.value, entry.position)
        for entry in profile.preference_entries
    ] == [
        ("dietary_preferences", "classic", 0),
        ("pain_points", "new", 0),
    ]
