import hashlib


def redact_barcode(barcode: str | None) -> str:
    if not barcode:
        return "missing"
    suffix = barcode[-4:] if len(barcode) >= 4 else barcode
    digest = hashlib.sha256(barcode.encode("utf-8")).hexdigest()[:8]
    return f"sha256:{digest}:*{suffix}"

