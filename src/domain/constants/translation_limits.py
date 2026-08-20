"""Provider-neutral resource ceilings for translation batches."""

from __future__ import annotations

MAX_TRANSLATION_ITEMS = 128
MAX_TRANSLATION_ITEM_BYTES = 4096
MAX_TRANSLATION_BATCH_BYTES = 32768


def translation_batch_within_limits(texts: list[str] | tuple[str, ...]) -> bool:
    """Check item count and UTF-8 byte ceilings before provider invocation."""
    if len(texts) > MAX_TRANSLATION_ITEMS:
        return False
    item_sizes = [len(text.encode("utf-8")) for text in texts]
    return (
        all(size <= MAX_TRANSLATION_ITEM_BYTES for size in item_sizes)
        and sum(item_sizes) <= MAX_TRANSLATION_BATCH_BYTES
    )


def iter_translation_batches(texts: list[str] | tuple[str, ...]) -> list[list[str]]:
    """Split texts into provider-safe batches without dropping in-limit items."""

    batches: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0
    for text in texts:
        size = len(text.encode("utf-8"))
        if size > MAX_TRANSLATION_ITEM_BYTES:
            continue
        if current and (
            len(current) >= MAX_TRANSLATION_ITEMS
            or current_bytes + size > MAX_TRANSLATION_BATCH_BYTES
        ):
            batches.append(current)
            current = []
            current_bytes = 0
        current.append(text)
        current_bytes += size
    if current:
        batches.append(current)
    return batches
