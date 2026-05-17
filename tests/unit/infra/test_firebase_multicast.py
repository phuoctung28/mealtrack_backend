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


def test_send_notification_sets_ios_time_sensitive_payload(monkeypatch):
    from src.infra.services import firebase_service as firebase_module
    from src.infra.services.firebase_service import FirebaseService

    captured = {}

    class FakeMulticastMessage:
        def __init__(self, **kwargs):
            captured["message"] = kwargs

    class FakeResponse:
        success_count = 1
        failure_count = 0
        responses = []

    class FakeValue:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(
        firebase_module.messaging,
        "MulticastMessage",
        FakeMulticastMessage,
    )
    monkeypatch.setattr(firebase_module.messaging, "Notification", FakeValue)
    monkeypatch.setattr(firebase_module.messaging, "AndroidConfig", FakeValue)
    monkeypatch.setattr(firebase_module.messaging, "AndroidNotification", FakeValue)
    monkeypatch.setattr(firebase_module.messaging, "APNSConfig", FakeValue)
    monkeypatch.setattr(firebase_module.messaging, "APNSPayload", FakeValue)
    monkeypatch.setattr(firebase_module.messaging, "Aps", FakeValue)
    monkeypatch.setattr(firebase_module.messaging, "ApsAlert", FakeValue)
    monkeypatch.setattr(
        firebase_module.messaging,
        "send_each_for_multicast",
        MagicMock(return_value=FakeResponse()),
    )

    svc = FirebaseService.__new__(FirebaseService)
    result = svc._send_to_tokens(["tok"], "Lunch", "Log your meal", {"type": "meal"})

    aps = captured["message"]["apns"].kwargs["payload"].kwargs["aps"]
    assert result["success"] is True
    assert "apns-interruption-level" not in captured["message"]["apns"].kwargs["headers"]
    assert aps.kwargs["custom_data"] == {"interruption-level": "time-sensitive"}
