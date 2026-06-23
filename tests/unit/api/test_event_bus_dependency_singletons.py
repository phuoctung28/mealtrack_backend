import importlib

import pytest


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

    # Patch MealGenerationService + translation service referenced in function.
    # These are locally imported inside get_food_search_event_bus(), so we must
    # patch the source module, not the event_bus module attribute.
    class _MealGen:
        pass

    class _Translator:
        def __init__(self, *args, **kwargs):
            pass

    import src.infra.adapters.meal_generation_service as _meal_gen_mod

    monkeypatch.setattr(_meal_gen_mod, "MealGenerationService", _MealGen)
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
    monkeypatch.setattr(deps, "get_suggestion_orchestration_service", lambda: object())
    monkeypatch.setattr(deps, "get_deepl_meal_translation_service", lambda: object())

    class _MealGen:
        pass

    import src.infra.adapters.meal_generation_service as _meal_gen_mod

    monkeypatch.setattr(_meal_gen_mod, "MealGenerationService", _MealGen)

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
    ]

    for name in handler_names:
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, lambda *a, **k: object())

    bus1 = mod.get_configured_event_bus()
    bus2 = mod.get_configured_event_bus()
    assert bus1 is bus2
    # Sanity: lots of registrations should have happened.
    assert len(bus1.handlers) > 10
    assert len(bus1.subscriptions) == 0


@pytest.mark.asyncio
async def test_configured_event_bus_can_send_movement_catalog_query(monkeypatch):
    mod = importlib.import_module("src.api.dependencies.event_bus")
    monkeypatch.setattr(mod, "_configured_event_bus", None, raising=False)

    class _Bus:
        def __init__(self):
            self.handlers = {}

        def register_handler(self, event_type, handler):
            self.handlers[event_type] = handler

        def subscribe(self, *args, **kwargs):
            pass

        async def send(self, event):
            event_type = type(event)
            if event_type not in self.handlers:
                raise ValueError(f"No handler registered for {event_type.__name__}")
            return await self.handlers[event_type].handle(event)

    monkeypatch.setattr(mod, "PyMediatorEventBus", _Bus)

    import src.api.base_dependencies as deps

    monkeypatch.setattr(deps, "get_image_store", lambda: object())
    monkeypatch.setattr(deps, "get_vision_service", lambda: object())
    monkeypatch.setattr(deps, "get_gpt_parser", lambda: object())
    monkeypatch.setattr(deps, "get_food_cache_service", lambda: object())
    monkeypatch.setattr(deps, "get_food_data_service", lambda: object())
    monkeypatch.setattr(deps, "get_food_mapping_service", lambda: object())
    monkeypatch.setattr(deps, "get_fat_secret_service_instance", lambda: object())
    monkeypatch.setattr(deps, "get_cache_service", lambda: object())
    monkeypatch.setattr(deps, "get_suggestion_orchestration_service", lambda: object())
    monkeypatch.setattr(deps, "get_deepl_meal_translation_service", lambda: object())

    class _MealGen:
        pass

    import src.infra.adapters.meal_generation_service as _meal_gen_mod

    monkeypatch.setattr(_meal_gen_mod, "MealGenerationService", _MealGen)

    class _StubWithHandle:
        async def handle(self, *args, **kwargs):
            return None

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
        "GetNutritionBulkQueryHandler",
        "GetActivitiesPresenceQueryHandler",
        "GetDailyActivitiesQueryHandler",
        "GetBulkActivitiesQueryHandler",
        "GetMealsByDateQueryHandler",
        "DiscoverMealsCommandHandler",
        "GenerateMealRecipesCommandHandler",
        "SaveMealSuggestionCommandHandler",
        "SaveUserOnboardingCommandHandler",
        "SyncUserCommandHandler",
        "UpdateUserLastAccessedCommandHandler",
        "CompleteOnboardingCommandHandler",
        "DeleteUserCommandHandler",
        "UpdateUserMetricsCommandHandler",
        "UpdateTimezoneCommandHandler",
        "UpdateLanguageCommandHandler",
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
        "MarkCheatDayCommandHandler",
        "UnmarkCheatDayCommandHandler",
        "GetCheatDaysQueryHandler",
        "AddWeightEntryCommandHandler",
        "DeleteWeightEntryCommandHandler",
        "SyncWeightEntriesCommandHandler",
        "GetWeightEntriesQueryHandler",
        "SaveSuggestionCommandHandler",
        "DeleteSavedSuggestionCommandHandler",
        "GetSavedSuggestionsQueryHandler",
    ]

    for name in handler_names:
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, lambda *a, **k: _StubWithHandle())

    from src.app.queries.movement import GetMovementCatalogQuery

    bus = mod.get_configured_event_bus()
    result = await bus.send(GetMovementCatalogQuery())

    assert result["activities"]
