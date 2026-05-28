import inspect


def test_gc_collect_present_in_send_due_notifications():
    from src.infra.services.scheduled_notification_service import ScheduledNotificationService
    source = inspect.getsource(ScheduledNotificationService._send_due_notifications)
    assert "gc.collect()" in source, "_send_due_notifications must call gc.collect()"


def test_gc_collect_present_in_precompute_db_sync():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService
    source = inspect.getsource(DailyContextPrecomputeService._precompute_db_sync)
    assert "gc.collect()" in source, "_precompute_db_sync must call gc.collect()"


def test_gc_imported_in_notification_service():
    import src.infra.services.scheduled_notification_service as mod
    assert "gc" in dir(mod) or hasattr(mod, "gc"), "gc must be imported in scheduled_notification_service"


def test_gc_imported_in_precompute_service():
    import src.infra.services.daily_context_precompute_service as mod
    assert "gc" in dir(mod) or hasattr(mod, "gc"), "gc must be imported in daily_context_precompute_service"
