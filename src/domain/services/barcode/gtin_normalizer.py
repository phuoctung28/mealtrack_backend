from dataclasses import dataclass

from src.domain.exceptions.barcode_exceptions import InvalidBarcodeError

GTIN_LENGTHS = {8, 12, 13, 14}


@dataclass(frozen=True)
class BarcodeLookupKeys:
    raw: str
    gtin: str
    gtin_13: str | None
    gtin_14: str
    aliases: tuple[str, ...]


def normalize_gtin(value: str) -> BarcodeLookupKeys:
    digits = _digits_only(value)
    if len(digits) not in GTIN_LENGTHS:
        raise InvalidBarcodeError("Barcode must be GTIN-8, GTIN-12, GTIN-13, or GTIN-14")
    if not _has_valid_check_digit(digits):
        raise InvalidBarcodeError("Invalid barcode check digit")

    gtin_13 = digits.zfill(13) if len(digits) <= 13 else None
    gtin_14 = digits.zfill(14)
    aliases = _aliases(digits, gtin_13, gtin_14)
    return BarcodeLookupKeys(
        raw=digits,
        gtin=digits,
        gtin_13=gtin_13,
        gtin_14=gtin_14,
        aliases=aliases,
    )


def _digits_only(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch not in {" ", "-"})
    if not cleaned or not cleaned.isdigit():
        raise InvalidBarcodeError("Barcode must contain only digits")
    return cleaned


def _has_valid_check_digit(digits: str) -> bool:
    body = digits[:-1]
    expected = _calculate_check_digit(body)
    return expected == int(digits[-1])


def _calculate_check_digit(body: str) -> int:
    total = 0
    for index, char in enumerate(reversed(body)):
        weight = 3 if index % 2 == 0 else 1
        total += int(char) * weight
    return (10 - (total % 10)) % 10


def _aliases(gtin: str, gtin_13: str | None, gtin_14: str) -> tuple[str, ...]:
    candidates = [gtin, gtin_13, gtin_14]
    if len(gtin) == 12:
        candidates.append(gtin.zfill(13))
    if len(gtin) == 13 and gtin.startswith("0"):
        candidates.append(gtin[1:])
    if len(gtin) == 14 and gtin.startswith("0"):
        candidates.append(gtin[1:])
        if gtin.startswith("00"):
            candidates.append(gtin[2:])

    seen: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.append(candidate)
    return tuple(seen)

