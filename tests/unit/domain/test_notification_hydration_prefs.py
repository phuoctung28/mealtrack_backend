def test_notification_preferences_has_hydration_reminders_enabled():
    from src.domain.model.notification.notification_preferences import NotificationPreferences
    import uuid
    prefs = NotificationPreferences(
        preferences_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )
    assert prefs.hydration_reminders_enabled is True


def test_create_default_has_hydration_reminders_enabled():
    from src.domain.model.notification.notification_preferences import NotificationPreferences
    import uuid
    prefs = NotificationPreferences.create_default(str(uuid.uuid4()))
    assert prefs.hydration_reminders_enabled is True


def test_update_preferences_toggles_hydration_reminders():
    from src.domain.model.notification.notification_preferences import NotificationPreferences
    import uuid
    prefs = NotificationPreferences.create_default(str(uuid.uuid4()))
    updated = prefs.update_preferences(hydration_reminders_enabled=False)
    assert updated.hydration_reminders_enabled is False
