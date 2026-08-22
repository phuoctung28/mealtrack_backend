import pytest

from src.domain.exceptions.barcode_exceptions import InvalidBarcodeError
from src.domain.services.barcode.gtin_normalizer import normalize_gtin


@pytest.mark.parametrize(
    "barcode,gtin_14",
    [
        ("96385074", "00000096385074"),
        ("036000291452", "00036000291452"),
        ("4006381333931", "04006381333931"),
        ("00036000291452", "00036000291452"),
    ],
)
def test_normalize_gtin_accepts_valid_lengths(barcode, gtin_14):
    keys = normalize_gtin(barcode)

    assert keys.raw == barcode
    assert keys.gtin_14 == gtin_14
    assert gtin_14 in keys.aliases


def test_normalize_gtin_strips_common_separators():
    keys = normalize_gtin("036000-291 452")

    assert keys.raw == "036000291452"
    assert keys.gtin_14 == "00036000291452"


@pytest.mark.parametrize("barcode", ["abc", "123", "036000291453"])
def test_normalize_gtin_rejects_invalid_input(barcode):
    with pytest.raises(InvalidBarcodeError):
        normalize_gtin(barcode)

