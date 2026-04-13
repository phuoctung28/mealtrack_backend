"""
Unit tests for FoodReferenceRepository.upsert_by_normalized_name
and find_by_normalized_name.

Test layers:
1. InMemoryFoodReferenceStore — in-memory stub that exercises business logic
   (is_verified protection, create/update semantics) without a live DB.
2. TestUniqueConstraintBehavior — mocks the real FoodReferenceRepository to
   verify C5 fixes: mysql_insert ON DUPLICATE KEY UPDATE used in the update
   path, and .scalars().first() used in find_by_normalized_name (C5 defensive).
"""
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, patch, call, PropertyMock
import pytest


# ---------------------------------------------------------------------------
# In-memory stub that mirrors the two new repository methods
# ---------------------------------------------------------------------------

class InMemoryFoodReferenceStore:
    """Minimal in-memory backing store used to drive stub assertions."""

    def __init__(self):
        self._rows: Dict[str, Dict[str, Any]] = {}  # keyed by name_normalized
        self._next_id = 1

    def find_by_normalized_name(self, name_normalized: str) -> Optional[Dict[str, Any]]:
        return self._rows.get(name_normalized)

    def upsert_by_normalized_name(
        self,
        name: str,
        name_normalized: str,
        protein_100g: float,
        carbs_100g: float,
        fat_100g: float,
        fiber_100g: float,
        sugar_100g: float,
        source: str,
        is_verified: bool,
        external_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        existing = self._rows.get(name_normalized)

        if existing is not None:
            if existing["is_verified"] and not is_verified:
                return existing  # preserve verified — no overwrite

            existing.update(
                name=name,
                protein_100g=protein_100g,
                carbs_100g=carbs_100g,
                fat_100g=fat_100g,
                fiber_100g=fiber_100g,
                sugar_100g=sugar_100g,
                source=source,
                is_verified=is_verified,
            )
            return existing

        row = {
            "id": self._next_id,
            "name": name,
            "name_normalized": name_normalized,
            "protein_100g": protein_100g,
            "carbs_100g": carbs_100g,
            "fat_100g": fat_100g,
            "fiber_100g": fiber_100g,
            "sugar_100g": sugar_100g,
            "source": source,
            "is_verified": is_verified,
            "external_id": external_id,
        }
        self._next_id += 1
        self._rows[name_normalized] = row
        return row


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store():
    return InMemoryFoodReferenceStore()


def _upsert(store: InMemoryFoodReferenceStore, **overrides) -> Optional[Dict[str, Any]]:
    """Helper that calls upsert_by_normalized_name with sensible defaults."""
    defaults = dict(
        name="chicken breast",
        name_normalized="chicken breast",
        protein_100g=23.1,
        carbs_100g=0.0,
        fat_100g=2.6,
        fiber_100g=0.0,
        sugar_100g=0.0,
        source="fatsecret",
        is_verified=False,
        external_id="fs-1",
    )
    defaults.update(overrides)
    return store.upsert_by_normalized_name(**defaults)


# ---------------------------------------------------------------------------
# find_by_normalized_name
# ---------------------------------------------------------------------------

class TestFindByNormalizedName:
    def test_returns_none_when_not_found(self, store):
        assert store.find_by_normalized_name("nonexistent") is None

    def test_returns_row_after_insert(self, store):
        _upsert(store)
        result = store.find_by_normalized_name("chicken breast")
        assert result is not None
        assert result["name"] == "chicken breast"

    def test_exact_match_only(self, store):
        _upsert(store, name_normalized="chicken breast")
        assert store.find_by_normalized_name("chicken") is None
        assert store.find_by_normalized_name("chicken breast extra") is None


# ---------------------------------------------------------------------------
# upsert_by_normalized_name — creates new entry
# ---------------------------------------------------------------------------

class TestUpsertCreatesNew:
    def test_creates_entry_when_none_exists(self, store):
        result = _upsert(store)
        assert result is not None
        assert result["protein_100g"] == pytest.approx(23.1)
        assert result["source"] == "fatsecret"
        assert result["is_verified"] is False

    def test_created_entry_is_findable(self, store):
        _upsert(store)
        found = store.find_by_normalized_name("chicken breast")
        assert found is not None
        assert found["protein_100g"] == pytest.approx(23.1)

    def test_assigns_id_to_new_entry(self, store):
        result = _upsert(store)
        assert result["id"] is not None

    def test_multiple_distinct_entries_created(self, store):
        _upsert(store, name="chicken breast", name_normalized="chicken breast")
        _upsert(store, name="white rice", name_normalized="white rice", protein_100g=2.7)
        assert store.find_by_normalized_name("chicken breast") is not None
        assert store.find_by_normalized_name("white rice") is not None


# ---------------------------------------------------------------------------
# upsert_by_normalized_name — updates existing unverified entry
# ---------------------------------------------------------------------------

class TestUpsertUpdatesUnverified:
    def test_updates_existing_unverified_entry(self, store):
        _upsert(store, protein_100g=20.0)
        result = _upsert(store, protein_100g=23.1)
        assert result["protein_100g"] == pytest.approx(23.1)

    def test_updated_entry_reflected_in_find(self, store):
        _upsert(store, fat_100g=1.0)
        _upsert(store, fat_100g=2.6)
        found = store.find_by_normalized_name("chicken breast")
        assert found["fat_100g"] == pytest.approx(2.6)

    def test_upsert_updates_source_field(self, store):
        _upsert(store, source="fatsecret")
        result = _upsert(store, source="usda")
        assert result["source"] == "usda"


# ---------------------------------------------------------------------------
# upsert_by_normalized_name — preserves is_verified=True entries
# ---------------------------------------------------------------------------

class TestUpsertPreservesVerifiedEntries:
    def test_does_not_overwrite_verified_with_unverified(self, store):
        # Seed a verified (curated) entry
        _upsert(store, protein_100g=31.0, is_verified=True, source="usda_curated")

        # Automated FatSecret lookup with lower-quality data attempts overwrite
        result = _upsert(store, protein_100g=20.0, is_verified=False, source="fatsecret")

        # Original curated values must be preserved
        assert result["protein_100g"] == pytest.approx(31.0)
        assert result["is_verified"] is True
        assert result["source"] == "usda_curated"

    def test_verified_overwrite_preserves_all_fields(self, store):
        _upsert(
            store,
            protein_100g=31.0,
            carbs_100g=0.5,
            fat_100g=3.6,
            is_verified=True,
            source="usda_curated",
        )
        _upsert(
            store,
            protein_100g=99.0,
            carbs_100g=99.0,
            fat_100g=99.0,
            is_verified=False,
        )

        found = store.find_by_normalized_name("chicken breast")
        assert found["protein_100g"] == pytest.approx(31.0)
        assert found["carbs_100g"] == pytest.approx(0.5)
        assert found["fat_100g"] == pytest.approx(3.6)

    def test_verified_can_overwrite_another_verified(self, store):
        """A verified update may overwrite another verified entry (curated → re-curated)."""
        _upsert(store, protein_100g=31.0, is_verified=True, source="usda")
        result = _upsert(store, protein_100g=32.0, is_verified=True, source="usda_v2")
        assert result["protein_100g"] == pytest.approx(32.0)
        assert result["source"] == "usda_v2"

    def test_unverified_can_be_promoted_to_verified(self, store):
        """An unverified entry can be upgraded to verified by a curated import."""
        _upsert(store, protein_100g=20.0, is_verified=False, source="fatsecret")
        result = _upsert(store, protein_100g=31.0, is_verified=True, source="usda_curated")
        assert result["is_verified"] is True
        assert result["protein_100g"] == pytest.approx(31.0)


# ---------------------------------------------------------------------------
# C5: Real repo uses ON DUPLICATE KEY UPDATE (atomic, race-safe)
# ---------------------------------------------------------------------------

class TestUniqueConstraintBehavior:
    """Verify the real FoodReferenceRepository C5 fixes without a live DB."""

    def _make_model(self, name_normalized: str, is_verified: bool = False) -> MagicMock:
        """Build a minimal FoodReferenceModel mock."""
        m = MagicMock()
        m.name_normalized = name_normalized
        m.is_verified = is_verified
        m.id = 1
        m.name = "chicken breast"
        m.name_vi = None
        m.brand = None
        m.category = None
        m.region = "global"
        m.fdc_id = None
        m.protein_100g = 23.0
        m.carbs_100g = 0.0
        m.fat_100g = 2.5
        m.fiber_100g = 0.0
        m.sugar_100g = 0.0
        m.serving_sizes = None
        m.density = 1.0
        m.serving_size = None
        m.extra_nutrients = None
        m.source = "fatsecret"
        m.image_url = None
        return m

    def test_find_by_normalized_name_uses_scalars_first(self):
        """C5: find_by_normalized_name must use .scalars().first() not scalar_one_or_none()."""
        from src.infra.repositories.food_reference_repository import FoodReferenceRepository

        mock_model = self._make_model("chicken breast")
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_model

        mock_execute = MagicMock()
        mock_execute.scalars.return_value = mock_scalars

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_execute

        with patch("src.infra.repositories.food_reference_repository.SessionLocal",
                   return_value=mock_session):
            repo = FoodReferenceRepository()
            result = repo.find_by_normalized_name("chicken breast")

        # Must call .scalars().first(), not scalar_one_or_none()
        mock_execute.scalars.assert_called_once()
        mock_scalars.first.assert_called_once()
        assert result is not None

    def test_upsert_by_normalized_name_uses_on_duplicate_key_update_for_new_entry(self):
        """C5: insert path uses mysql_insert().values().on_duplicate_key_update() — not session.add()."""
        from src.infra.repositories.food_reference_repository import FoodReferenceRepository

        # First SELECT returns None (no existing row)
        mock_scalars_select = MagicMock()
        mock_scalars_select.first.return_value = None
        mock_execute_select = MagicMock()
        mock_execute_select.scalars.return_value = mock_scalars_select

        # Second SELECT (re-fetch after upsert) returns a model
        mock_model = self._make_model("chicken breast")
        mock_scalars_refetch = MagicMock()
        mock_scalars_refetch.first.return_value = mock_model
        mock_execute_refetch = MagicMock()
        mock_execute_refetch.scalars.return_value = mock_scalars_refetch

        execute_calls = [mock_execute_select, MagicMock(), mock_execute_refetch]
        call_counter = {"n": 0}

        def execute_side_effect(stmt):
            idx = call_counter["n"]
            call_counter["n"] += 1
            return execute_calls[idx] if idx < len(execute_calls) else MagicMock()

        mock_session = MagicMock()
        mock_session.execute.side_effect = execute_side_effect

        # Track the full call chain: mysql_insert(Model).values(...).on_duplicate_key_update(...)
        # Each method in the chain returns the same fluent mock so we can assert on it.
        fluent_stmt = MagicMock()
        fluent_stmt.values.return_value = fluent_stmt
        fluent_stmt.on_duplicate_key_update.return_value = fluent_stmt

        with patch("src.infra.repositories.food_reference_repository.SessionLocal",
                   return_value=mock_session):
            with patch("src.infra.repositories.food_reference_repository.mysql_insert",
                       return_value=fluent_stmt):
                repo = FoodReferenceRepository()
                repo.upsert_by_normalized_name(
                    name="chicken breast",
                    name_normalized="chicken breast",
                    protein_100g=23.0,
                    carbs_100g=0.0,
                    fat_100g=2.5,
                    fiber_100g=0.0,
                    sugar_100g=0.0,
                    source="fatsecret",
                    is_verified=False,
                )

        # .values() and .on_duplicate_key_update() must both be called → atomic upsert
        fluent_stmt.values.assert_called_once()
        fluent_stmt.on_duplicate_key_update.assert_called_once()
        # session.add() must NOT be called (not a plain ORM insert)
        mock_session.add.assert_not_called()

    def test_upsert_verified_protection_skips_atomic_upsert(self):
        """C5: verified protection must short-circuit before the ON DUPLICATE KEY UPDATE."""
        from src.infra.repositories.food_reference_repository import FoodReferenceRepository

        verified_model = self._make_model("chicken breast", is_verified=True)
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = verified_model

        mock_execute = MagicMock()
        mock_execute.scalars.return_value = mock_scalars

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_execute

        with patch("src.infra.repositories.food_reference_repository.SessionLocal",
                   return_value=mock_session):
            with patch("src.infra.repositories.food_reference_repository.mysql_insert") as mock_insert:
                repo = FoodReferenceRepository()
                result = repo.upsert_by_normalized_name(
                    name="chicken breast",
                    name_normalized="chicken breast",
                    protein_100g=99.0,  # would overwrite if not protected
                    carbs_100g=0.0,
                    fat_100g=0.0,
                    fiber_100g=0.0,
                    sugar_100g=0.0,
                    source="fatsecret",
                    is_verified=False,  # incoming unverified — must be blocked
                )

        # mysql_insert must NOT have been called — we short-circuited
        mock_insert.assert_not_called()
        # Returned value must reflect the original verified row (protein=23.0, not 99.0)
        assert result is not None
        assert result["protein_100g"] == pytest.approx(23.0)
