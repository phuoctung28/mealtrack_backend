"""Snapshot tests for Android FCM payload builder."""

from firebase_admin._messaging_encoder import MessageEncoder

from src.infra.services.push.android_payload_builder import (
    HIGH_PRIORITY_CHANNEL_ID,
    build_android_config,
)


def _serialize(cfg):
    return MessageEncoder.encode_android(cfg)


class TestAndroidPayloadBuilder:
    def test_priority_high(self):
        cfg = build_android_config()
        encoded = _serialize(cfg)
        assert encoded["priority"] == "high"

    def test_high_priority_channel_default(self):
        cfg = build_android_config()
        encoded = _serialize(cfg)
        assert encoded["notification"]["channel_id"] == HIGH_PRIORITY_CHANNEL_ID

    def test_custom_channel_id(self):
        cfg = build_android_config(channel_id="custom_channel")
        encoded = _serialize(cfg)
        assert encoded["notification"]["channel_id"] == "custom_channel"

    def test_sound_default(self):
        cfg = build_android_config()
        encoded = _serialize(cfg)
        assert encoded["notification"]["sound"] == "default"
