"""Snapshot tests for APNs payload builder.

Uses firebase-admin's internal `MessageEncoder` to serialize `APNSConfig`
to a dict, then asserts the wire-format structure. Pinning
`firebase-admin>=6.0.0,<7.0.0` in requirements.txt keeps this stable.
"""

from firebase_admin._messaging_encoder import MessageEncoder

from src.infra.services.push.apns_payload_builder import build_apns_config


def _serialize(cfg):
    return MessageEncoder.encode_apns(cfg)


class TestApnsPayloadBuilder:
    def test_interruption_level_in_payload_body(self):
        cfg = build_apns_config(title="Test", body="Body")
        encoded = _serialize(cfg)
        assert encoded["payload"]["aps"]["interruption-level"] == "time-sensitive"

    def test_interruption_level_not_in_headers(self):
        cfg = build_apns_config(title="Test", body="Body")
        encoded = _serialize(cfg)
        headers = encoded.get("headers", {})
        assert "apns-interruption-level" not in headers

    def test_required_apns_headers(self):
        cfg = build_apns_config(title="Test", body="Body")
        encoded = _serialize(cfg)
        assert encoded["headers"]["apns-priority"] == "10"
        assert encoded["headers"]["apns-push-type"] == "alert"

    def test_alert_title_and_body(self):
        cfg = build_apns_config(title="Meal", body="Breakfast time")
        encoded = _serialize(cfg)
        assert encoded["payload"]["aps"]["alert"]["title"] == "Meal"
        assert encoded["payload"]["aps"]["alert"]["body"] == "Breakfast time"

    def test_mutable_content_set(self):
        cfg = build_apns_config(title="t", body="b")
        encoded = _serialize(cfg)
        assert encoded["payload"]["aps"]["mutable-content"] == 1

    def test_sound_and_badge(self):
        cfg = build_apns_config(title="t", body="b")
        encoded = _serialize(cfg)
        assert encoded["payload"]["aps"]["sound"] == "default"
        assert encoded["payload"]["aps"]["badge"] == 1

    def test_empty_title_omits_title_key(self):
        """Empty title must serialize as absent (not empty string) per APNs spec.

        Empty string for `aps.alert.title` is undefined behavior on iOS 15+ Time
        Sensitive and may suppress the banner. The builder maps "" → None so
        firebase-admin omits the key entirely.
        """
        cfg = build_apns_config(title="", body="Body only")
        encoded = _serialize(cfg)
        alert = encoded["payload"]["aps"]["alert"]
        assert "title" not in alert, f"title key must be absent, got {alert}"
        assert alert["body"] == "Body only"
