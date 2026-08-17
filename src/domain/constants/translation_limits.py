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
