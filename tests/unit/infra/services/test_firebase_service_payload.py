"""Integration-style snapshot tests for FirebaseService payload construction.

Verifies that both `_send_to_tokens` (multicast) and `send_to_topic` produce
messages with title/body in `data`, no top-level notification field, and APNs
display text plus `interruption-level: time-sensitive` in the payload body.
"""

from unittest.mock import MagicMock, patch

from firebase_admin._messaging_encoder import MessageEncoder

from src.infra.services.firebase_service import FirebaseService


class TestFirebaseServicePayload:
    def test_send_to_tokens_data_only_no_notification_field(self):
        svc = FirebaseService.__new__(FirebaseService)
        with patch(
            "src.infra.services.firebase_service.firebase_admin"
        ) as mock_admin, patch(
            "src.infra.services.firebase_service.messaging.send_each_for_multicast"
        ) as mock_send:
            mock_admin._apps = {"default": object()}
            mock_send.return_value = MagicMock(
                success_count=1, failure_count=0, responses=[]
            )
            svc._send_to_tokens(["tok"], "T", "B", {"type": "meal_reminder_lunch"})

        sent_msg = mock_send.call_args[0][0]

        # No top-level notification field.
        assert sent_msg.notification is None

        # Title/body migrated into data dict
        assert sent_msg.data["title"] == "T"
        assert sent_msg.data["body"] == "B"
        assert sent_msg.data["type"] == "meal_reminder_lunch"

        # APNs payload has interruption-level in payload body, not headers
        apns_dict = MessageEncoder.encode_apns(sent_msg.apns)
        assert (
            apns_dict["payload"]["aps"]["interruption-level"] == "time-sensitive"
        )
        assert "apns-interruption-level" not in apns_dict.get("headers", {})
        assert sent_msg.data["title"] == "T"
        assert sent_msg.data["body"] == "B"
        assert apns_dict["payload"]["aps"]["alert"]["title"] == "T"
        assert apns_dict["payload"]["aps"]["alert"]["body"] == "B"

    def test_send_to_topic_data_only_no_notification_field(self):
        svc = FirebaseService.__new__(FirebaseService)
        with patch(
            "src.infra.services.firebase_service.firebase_admin"
        ) as mock_admin, patch(
            "src.infra.services.firebase_service.messaging.send"
        ) as mock_send:
            mock_admin._apps = {"default": object()}
            mock_send.return_value = "projects/p/messages/123"
            svc.send_to_topic("test_topic", "T", "B", {"type": "summary"})

        sent_msg = mock_send.call_args[0][0]

        # No top-level notification field.
        assert sent_msg.notification is None
        assert sent_msg.data["title"] == "T"
        assert sent_msg.data["body"] == "B"

        # APNs payload has interruption-level (same as multicast path)
        apns_dict = MessageEncoder.encode_apns(sent_msg.apns)
        assert (
            apns_dict["payload"]["aps"]["interruption-level"] == "time-sensitive"
        )
        assert apns_dict["payload"]["aps"]["alert"]["title"] == "T"
        assert apns_dict["payload"]["aps"]["alert"]["body"] == "B"

    def test_send_to_tokens_rejects_blank_ios_display_text(self):
        svc = FirebaseService.__new__(FirebaseService)
        with patch(
            "src.infra.services.firebase_service.firebase_admin"
        ) as mock_admin, patch(
            "src.infra.services.firebase_service.messaging.send_each_for_multicast"
        ) as mock_send:
            mock_admin._apps = {"default": object()}
            mock_send.return_value = MagicMock(
                success_count=1, failure_count=0, responses=[]
            )
            result = svc._send_to_tokens(["tok"], "", "  ", {"type": "daily_summary"})

        assert result["success"] is False
        assert result["reason"] == "send_error"
        assert "title and body must be non-empty" in result["error"]
        mock_send.assert_not_called()

    def test_send_to_topic_rejects_blank_ios_display_text(self):
        svc = FirebaseService.__new__(FirebaseService)
        with patch(
            "src.infra.services.firebase_service.firebase_admin"
        ) as mock_admin, patch(
            "src.infra.services.firebase_service.messaging.send"
        ) as mock_send:
            mock_admin._apps = {"default": object()}
            mock_send.return_value = "projects/p/messages/123"
            result = svc.send_to_topic("test_topic", "", "  ", {"type": "summary"})

        assert result["success"] is False
        assert result["reason"] == "send_error"
        assert "title and body must be non-empty" in result["error"]
        mock_send.assert_not_called()
