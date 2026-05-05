from unittest.mock import patch, MagicMock


def test_send_multicast_delegates_to_send_to_tokens():
    from src.infra.services.firebase_service import FirebaseService

    svc = FirebaseService.__new__(FirebaseService)
    svc._send_to_tokens = MagicMock(
        return_value={"success": True, "sent": 2, "failed": 0, "failed_tokens": []}
    )

    with patch("src.infra.services.firebase_service.firebase_admin") as mock_admin:
        mock_admin._apps = {"default": object()}
        result = svc.send_multicast(
            tokens=["tok1", "tok2"],
            title="Lunch time!",
            body="800 cal left",
            notification_type="meal_reminder_lunch",
        )

    svc._send_to_tokens.assert_called_once()
    assert result["success"] is True


def test_send_multicast_returns_not_initialized_when_firebase_not_ready():
    from src.infra.services.firebase_service import FirebaseService

    svc = FirebaseService.__new__(FirebaseService)

    with patch("src.infra.services.firebase_service.firebase_admin") as mock_admin:
        mock_admin._apps = {}
        result = svc.send_multicast(tokens=["tok"], title="t", body="b")

    assert result == {"success": False, "reason": "firebase_not_initialized"}
