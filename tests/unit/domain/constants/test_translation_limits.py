from src.domain.constants.translation_limits import (
    MAX_TRANSLATION_BATCH_BYTES,
    MAX_TRANSLATION_ITEM_BYTES,
    MAX_TRANSLATION_ITEMS,
    translation_batch_within_limits,
)


def test_translation_limits_are_provider_neutral():
    assert MAX_TRANSLATION_ITEMS == 128
    assert MAX_TRANSLATION_ITEM_BYTES == 4096
    assert MAX_TRANSLATION_BATCH_BYTES == 32768
    assert translation_batch_within_limits(["a" * 4096])
    assert not translation_batch_within_limits(["a" * 4097])
    assert not translation_batch_within_limits(["a"] * 129)

