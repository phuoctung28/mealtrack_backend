import importlib


def test_get_food_search_event_bus_is_singleton(monkeypatch):
    # Import fresh to reset module globals
    mod = importlib.import_module("src.api.dependencies.event_bus")
    monkeypatch.setattr(mod, "_food_search_event_bus", None, raising=False)

    # Patch PyMediatorEventBus to lightweight stub so we don't pull heavy deps
    class _Bus:
        def __init__(self):
            self.registered = []

        def register_handler(self, *args, **kwargs):
            self.registered.append((args, kwargs))

    monkeypatch.setattr(mod, "PyMediatorEventBus", _Bus)

    # Patch base dependency getters imported inside get_food_search_event_bus()
    import src.api.base_dependencies as deps

    monkeypatch.setattr(deps, "get_food_cache_service", lambda: object())
    monkeypatch.setattr(deps, "get_food_data_service", lambda: object())
    monkeypatch.setattr(deps, "get_food_mapping_service", lambda: object())
    monkeypatch.setattr(deps, "get_open_food_facts_service_instance", lambda: object())
    monkeypatch.setattr(deps, "get_fat_secret_service_instance", lambda: object())
    monkeypatch.setattr(deps, "get_food_reference_repository", lambda: object())

    # Patch MealGenerationService + translation service referenced in function
    class _MealGen:
        pass

    class _Translator:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(mod, "MealGenerationService", _MealGen, raising=False)
    monkeypatch.setattr(mod, "FoodSearchTranslationService", _Translator, raising=False)

    # Patch handlers to avoid constructing real ones
    monkeypatch.setattr(mod, "SearchFoodsQueryHandler", lambda *a, **k: object())
    monkeypatch.setattr(mod, "GetFoodDetailsQueryHandler", lambda *a, **k: object())
    monkeypatch.setattr(mod, "LookupBarcodeQueryHandler", lambda *a, **k: object())

    bus1 = mod.get_food_search_event_bus()
    bus2 = mod.get_food_search_event_bus()
    assert bus1 is bus2
    assert len(bus1.registered) == 3


def test_get_configured_event_bus_is_singleton(monkeypatch):
    mod = importlib.import_module("src.api.dependencies.event_bus")
    monkeypatch.setattr(mod, "_configured_event_bus", None, raising=False)

    class _Bus:
        def __init__(self):
            self.handlers = []
            self.subscriptions = []

        def register_handler(self, *args, **kwargs):
            self.handlers.append((args, kwargs))

        def subscribe(self, *args, **kwargs):
            self.subscriptions.append((args, kwargs))

    monkeypatch.setattr(mod, "PyMediatorEventBus", _Bus)

    # Patch base dependency getters imported inside get_configured_event_bus()
    import src.api.base_dependencies as deps

    monkeypatch.setattr(deps, "get_image_store", lambda: object())
    monkeypatch.setattr(deps, "get_vision_service", lambda: object())
    monkeypatch.setattr(deps, "get_gpt_parser", lambda: object())
    monkeypatch.setattr(deps, "get_food_cache_service", lambda: object())
    monkeypatch.setattr(deps, "get_food_data_service", lambda: object())
    monkeypatch.setattr(deps, "get_food_mapping_service", lambda: object())
    monkeypatch.setattr(deps, "get_fat_secret_service_instance", lambda: object())
    monkeypatch.setattr(deps, "get_cache_service", lambda: object())
    monkeypatch.setattr(deps, "get_ai_chat_service", lambda: object())
    monkeypatch.setattr(deps, "get_suggestion_orchestration_service", lambda: object())
    monkeypatch.setattr(deps, "get_deepl_meal_translation_service", lambda: object())

    # Patch every handler class referenced to cheap stubs.
    # They're imported in the module, so patching attributes is enough.
    handler_names = [
        "UploadMealImageImmediatelyHandler",
        "EditMealCommandHandler",
        "AddCustomIngredientCommandHandler",
        "DeleteMealCommandHandler",
        "CreateManualMealCommandHandler",
        "ParseMealTextHandler",
        "SearchFoodsQueryHandler",
        "GetFoodDetailsQueryHandler",
        "GetMealByIdQueryHandler",
        "GetDailyMacrosQueryHandler",
        "GetWeeklyBudgetQueryHandler",
        "GetStreakQueryHandler",
        "GetDailyBreakdownQueryHandler",
        "GetDailyActivitiesQueryHandler",
        "GenerateDailyMealSuggestionsCommandHandler",
        "GenerateSingleMealCommandHandler",
        "GetMealSuggestionsForProfileQueryHandler",
        "GetSingleMealForProfileQueryHandler",
        "GetMealPlanningSummaryQueryHandler",
        "GetMealsByDateQueryHandler",
        "GenerateMealSuggestionsCommandHandler",
        "SaveMealSuggestionCommandHandler",
        "SaveUserOnboardingCommandHandler",
        "SyncUserCommandHandler",
        "UpdateUserLastAccessedCommandHandler",
        "CompleteOnboardingCommandHandler",
        "DeleteUserCommandHandler",
        "UpdateUserMetricsCommandHandler",
        "UpdateTimezoneCommandHandler",
        "UpdateCustomMacrosCommandHandler",
        "GetUserProfileQueryHandler",
        "GetUserByFirebaseUidQueryHandler",
        "GetUserOnboardingStatusQueryHandler",
        "GetUserMetricsQueryHandler",
        "GetUserTdeeQueryHandler",
        "PreviewTdeeQueryHandler",
        "RegisterFcmTokenCommandHandler",
        "DeleteFcmTokenCommandHandler",
        "UpdateNotificationPreferencesCommandHandler",
        "GetNotificationPreferencesQueryHandler",
        "RecognizeIngredientCommandHandler",
        "CreateThreadCommandHandler",
        "SendMessageCommandHandler",
        "DeleteThreadCommandHandler",
        "GetThreadsQueryHandler",
        "GetThreadQueryHandler",
        "GetMessagesQueryHandler",
        "MarkCheatDayCommandHandler",
        "UnmarkCheatDayCommandHandler",
        "GetCheatDaysQueryHandler",
        "SaveSuggestionCommandHandler",
        "DeleteSavedSuggestionCommandHandler",
        "GetSavedSuggestionsQueryHandler",
        "MealAnalysisEventHandler",
    ]
    for name in handler_names:
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, lambda *a, **k: object())

    bus1 = mod.get_configured_event_bus()
    bus2 = mod.get_configured_event_bus()
    assert bus1 is bus2
    # Sanity: lots of registrations should have happened.
    assert len(bus1.handlers) > 10
    assert len(bus1.subscriptions) == 1

