from src.domain.services.hydration_catalog_service import (
    find_by_id,
    localized_name,
    localized_name_for_catalog_name,
)


def test_coke_zero_canonical_name_stays_english():
    drink = find_by_id("coke-zero")
    assert drink is not None
    assert drink.name == "Coke Zero"


def test_coke_zero_vietnamese_uses_coca_pepsi_zero():
    drink = find_by_id("coke-zero")
    assert localized_name(drink, "vi") == "Coca/Pepsi Zero"


def test_sparkling_vietnamese_uses_co_ga():
    drink = find_by_id("sparkling")
    assert localized_name(drink, "vi") == "Nước có ga"


def test_legacy_snapshots_still_localizes():
    assert localized_name_for_catalog_name("Coke Zero", "vi") == "Coca/Pepsi Zero"
    assert localized_name_for_catalog_name("Coca/Pepsi Zero", "en") == "Coke Zero"
    assert localized_name_for_catalog_name("Coke Zero", "en") == "Coke Zero"
