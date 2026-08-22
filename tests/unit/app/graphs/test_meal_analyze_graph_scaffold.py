"""Tests for the default-off meal analysis graph scaffold."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.api.exceptions import ValidationException
from src.app.commands.meal.scan_by_url_command import ScanByUrlCommand
from src.app.commands.meal.upload_meal_image_immediately_command import (
    UploadMealImageImmediatelyCommand,
)
from src.app.graphs.meal_analyze.graph import (
    build_meal_analyze_graph,
    run_meal_analyze_graph,
    run_meal_analyze_graph_async,
)
from src.app.graphs.meal_analyze.nodes import (
    acquire_image,
    analyze_vision,
    schedule_value_insights,
)
from src.app.graphs.meal_analyze.runtime import AcquiredImage, MealAnalyzeRuntime
from src.domain.exceptions.ai_exceptions import MealResponseLocalizationError
from src.domain.model.meal import MealStatus
from src.domain.model.meal.meal_response_localization import (
    parse_meal_response_localization,
)
from src.domain.parsers.vision_response_parser import VisionResponseParser
from src.infra.config.settings import Settings


class _FakeGraphUow:
    def __init__(self):
        self.users = AsyncMock()
        self.users.get_user_timezone = AsyncMock(return_value="UTC")
        self.meals = AsyncMock()
        self._saved_meals = []

        async def save_meal(meal):
            self._saved_meals.append(meal)
            return meal

        self.meals.save = AsyncMock(side_effect=save_meal)
        self.meals.find_by_id = AsyncMock(
            side_effect=lambda meal_id, **_: self._saved_meals[-1]
        )
        self.commit = AsyncMock()
        self.outbox = SimpleNamespace()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_meal_analyze_graph_settings_default_to_disabled(monkeypatch):
    monkeypatch.delenv("AI_MEAL_ANALYZE_GRAPH_ENABLED", raising=False)
    monkeypatch.delenv("AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED", raising=False)
    monkeypatch.delenv(
        "AI_MEAL_ANALYZE_EXTERNAL_PROVIDER_TIMEOUT_SECONDS", raising=False
    )
    monkeypatch.delenv("AI_MEAL_ANALYZE_GRAPH_VERSION", raising=False)
    settings = Settings(_env_file=None)

    assert settings.AI_MEAL_ANALYZE_GRAPH_ENABLED is False
    assert settings.AI_MEAL_ANALYZE_FATSECRET_VALIDATION_ENABLED is False
    assert settings.AI_MEAL_ANALYZE_EXTERNAL_PROVIDER_TIMEOUT_SECONDS == 5.0
    assert settings.AI_MEAL_ANALYZE_GRAPH_VERSION == "v1"


def test_build_meal_analyze_graph_compiles():
    graph = build_meal_analyze_graph()

    assert hasattr(graph, "invoke")


def test_run_meal_analyze_graph_preserves_input_compatible_state():
    result = run_meal_analyze_graph(
        {
            "scan_mode": "food_label",
            "image_id": "image-123",
            "user_id": "user-123",
            "target_date": None,
        }
    )

    assert result["image_id"] == "image-123"
    assert result["user_id"] == "user-123"
    assert result["selected_mode"] == "food_label"
    assert result["graph_version"] == "v1"
    assert result["prepared"] is True
    assert result["completed"] is True


@pytest.mark.asyncio
async def test_async_graph_runner_executes_runtime_bound_acquisition():
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value="https://res.cloudinary.com/demo/image/upload/mealtrack/image-123.jpg"
    )
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="user-123",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        image_store=image_store,
        image_id_factory=lambda: "image-123",
    )

    result = await run_meal_analyze_graph_async(
        {
            "scan_mode": "meal_scan",
            "user_id": "user-123",
            "target_date": None,
        },
        runtime,
    )

    assert result["image_id"] == "image-123"
    assert result["content_kind"] == "meal_image"
    assert result["image_size_bytes"] == len(b"upload-bytes")
    assert result["completed"] is True
    assert runtime.acquired_image is not None
    assert "image_url" not in result
    assert "image_bytes" not in result


@pytest.mark.asyncio
async def test_async_graph_runner_persists_ready_meal_and_invalidates_cache():
    image_id = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
    meal_id = "22222222-2222-4222-8222-222222222222"
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value=f"https://res.cloudinary.com/demo/image/upload/mealtrack/{image_id}.jpg"
    )
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "dish_name": "Chicken rice",
                "confidence": 0.91,
                "foods": [
                    {
                        "name": "Chicken rice",
                        "quantity_g": 300,
                        "confidence": 0.91,
                        "macros": {
                            "protein_g": 28,
                            "carbs_g": 52,
                            "fat_g": 8,
                            "fiber_g": 2,
                            "sugar_g": 1,
                        },
                    }
                ],
            }
        }
    )
    uow = _FakeGraphUow()
    cache = AsyncMock()
    cache.enqueue_meal_invalidation = AsyncMock()
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="00000000-0000-0000-0000-000000000001",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        image_store=image_store,
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        uow=uow,
        cache_invalidation=cache,
        image_id_factory=lambda: image_id,
        meal_id_factory=lambda: meal_id,
    )

    result = await run_meal_analyze_graph_async(
        {
            "scan_mode": "meal_scan",
            "user_id": runtime.command.user_id,
            "target_date": None,
        },
        runtime,
    )

    vision_service.analyze.assert_awaited_once_with(
        b"upload-bytes",
        language="en",
    )
    uow.meals.save.assert_awaited_once()
    cache.enqueue_meal_invalidation.assert_awaited_once()
    meal = result["result"]
    assert meal.meal_id == meal_id
    assert meal.status == MealStatus.READY
    assert meal.dish_name == "Chicken rice"
    assert meal.image.image_id == image_id
    assert result["meal_id"] == meal_id
    assert "image_url" not in result
    assert "image_bytes" not in result


@pytest.mark.asyncio
async def test_async_graph_runner_schedules_value_insights_after_cache_invalidation():
    image_id = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
    meal_id = "22222222-2222-4222-8222-222222222222"
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value=f"https://res.cloudinary.com/demo/image/upload/mealtrack/{image_id}.jpg"
    )
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "dish_name": "Chicken rice",
                "confidence": 0.91,
                "foods": [
                    {
                        "name": "Chicken rice",
                        "quantity_g": 300,
                        "confidence": 0.91,
                        "macros": {
                            "protein_g": 28,
                            "carbs_g": 52,
                            "fat_g": 8,
                            "fiber_g": 2,
                            "sugar_g": 1,
                        },
                    }
                ],
            }
        }
    )
    uow = _FakeGraphUow()
    cache = AsyncMock()
    cache.enqueue_meal_invalidation = AsyncMock()

    class TaskManager:
        def __init__(self):
            self.spawned = []

        def spawn(self, name, coroutine):
            self.spawned.append((name, coroutine))

    task_manager = TaskManager()
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="00000000-0000-0000-0000-000000000001",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        image_store=image_store,
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        uow=uow,
        cache_invalidation=cache,
        meal_value_insight_task_manager=task_manager,
        meal_value_insight_cache=AsyncMock(),
        meal_value_insight_ai_manager=AsyncMock(),
        event_bus=AsyncMock(),
        image_id_factory=lambda: image_id,
        meal_id_factory=lambda: meal_id,
    )

    result = await run_meal_analyze_graph_async(
        {
            "scan_mode": "meal_scan",
            "user_id": runtime.command.user_id,
            "target_date": None,
        },
        runtime,
    )

    cache.enqueue_meal_invalidation.assert_awaited_once()
    assert result["cache_invalidated"] is True
    assert result["meal_value_insight_scheduled"] is True
    assert result["meal_value_insight_source"] == "meal_analyze_graph"
    assert task_manager.spawned
    task_name, coroutine = task_manager.spawned[0]
    assert task_name == f"meal-value-insights:{meal_id}"
    coroutine.close()
    assert "meal_value_insight_task_manager" not in result
    assert "meal_value_insight_ai_manager" not in result
    assert "user_context" not in result


@pytest.mark.asyncio
async def test_graph_ready_response_returns_before_value_insight_ai_completes(caplog):
    image_id = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
    meal_id = "22222222-2222-4222-8222-222222222222"
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value=f"https://res.cloudinary.com/demo/image/upload/mealtrack/{image_id}.jpg"
    )
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "dish_name": "Chicken rice",
                "confidence": 0.91,
                "foods": [
                    {
                        "name": "Chicken rice",
                        "quantity_g": 300,
                        "confidence": 0.91,
                        "macros": {
                            "protein_g": 28,
                            "carbs_g": 52,
                            "fat_g": 8,
                            "fiber_g": 2,
                            "sugar_g": 1,
                        },
                    }
                ],
            }
        }
    )

    class CapturingTaskManager:
        def __init__(self):
            self.spawned = []

        def spawn(self, name, coroutine):
            self.spawned.append((name, coroutine))
            return coroutine

    class FakeCache:
        def __init__(self):
            self.saved = []

        async def get(self, key):
            return None

        async def set(self, key, value, ttl):
            self.saved.append((key, value, ttl))
            return True

    class FakeEventBus:
        async def send(self, query):
            return {"profile": {}, "tdee": {}}

    task_manager = CapturingTaskManager()
    cache = AsyncMock()
    cache.enqueue_meal_invalidation = AsyncMock()
    insight_cache = FakeCache()
    ai_manager = AsyncMock()
    ai_manager.generate = AsyncMock(
        return_value={
            "meal_bullets": [
                {
                    "text": "Protein supports fullness after this meal.",
                    "category": "benefit",
                    "highlights": ["fullness"],
                }
            ],
            "ingredient_insights": [],
        }
    )
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="00000000-0000-0000-0000-000000000001",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        image_store=image_store,
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        uow=_FakeGraphUow(),
        cache_invalidation=cache,
        meal_value_insight_task_manager=task_manager,
        meal_value_insight_cache=insight_cache,
        meal_value_insight_ai_manager=ai_manager,
        event_bus=FakeEventBus(),
        image_id_factory=lambda: image_id,
        meal_id_factory=lambda: meal_id,
    )

    result = await run_meal_analyze_graph_async(
        {
            "scan_mode": "meal_scan",
            "user_id": runtime.command.user_id,
            "target_date": None,
        },
        runtime,
    )

    assert result["result"].status == MealStatus.READY
    assert result["meal_value_insight_scheduled"] is True
    assert task_manager.spawned
    ai_manager.generate.assert_not_awaited()

    with caplog.at_level(
        "INFO", logger="src.domain.services.meal_value_insight_service"
    ):
        await task_manager.spawned[0][1]

    ai_manager.generate.assert_awaited_once()
    assert insight_cache.saved
    assert "meal_value_insights.cache_saved" in caplog.text


@pytest.mark.asyncio
async def test_schedule_value_insights_returns_ready_state_when_scheduler_fails():
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="user-1",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        meal_value_insight_task_manager=object(),
        meal_value_insight_cache=object(),
        meal_value_insight_ai_manager=AsyncMock(),
        event_bus=AsyncMock(),
    )
    runtime.saved_meal = type("Meal", (), {"meal_id": "meal-1"})()

    def failing_scheduler(*args, **kwargs):
        raise RuntimeError("scheduler unavailable")

    runtime.meal_value_insight_scheduler = failing_scheduler

    state_update = await schedule_value_insights({"meal_id": "meal-1"}, runtime)

    assert state_update == {
        "meal_value_insight_scheduled": False,
        "meal_value_insight_source": "meal_analyze_graph",
    }


@pytest.mark.asyncio
async def test_async_graph_runner_no_food_does_not_persist():
    image_id = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value=f"https://res.cloudinary.com/demo/image/upload/mealtrack/{image_id}.jpg"
    )
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        return_value={"structured_data": {"is_food": False, "foods": []}}
    )
    uow = _FakeGraphUow()
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="00000000-0000-0000-0000-000000000001",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        image_store=image_store,
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        uow=uow,
        image_id_factory=lambda: image_id,
    )

    with pytest.raises(
        ValidationException, match="Image does not appear to contain food"
    ):
        await run_meal_analyze_graph_async(
            {
                "scan_mode": "meal_scan",
                "user_id": runtime.command.user_id,
                "target_date": None,
            },
            runtime,
        )

    uow.meals.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_graph_food_label_crop_persists_original_image_reference():
    full_image_id = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
    crop_image_id = "33333333-3333-4333-8333-333333333333"
    full_url = (
        f"https://res.cloudinary.com/demo/image/upload/mealtrack/{full_image_id}.jpg"
    )
    crop_url = (
        f"https://res.cloudinary.com/demo/image/upload/mealtrack/{crop_image_id}.jpg"
    )
    download_image_bytes = AsyncMock(return_value=b"crop-label-bytes")
    vision_service = AsyncMock()
    vision_service.analyze_with_strategy = AsyncMock(
        return_value={
            "structured_data": {
                "is_food_label": True,
                "product_name": "Protein Bar",
                "brand": None,
                "serving_size": {"display_text": "50g", "grams": 50},
                "servings_per_package": 1,
                "label_calories_per_serving": 180,
                "macros_per_serving": {
                    "protein_g": 12,
                    "carbs_g": 20,
                    "fat_g": 6,
                    "fiber_g": 3,
                    "sugar_g": 8,
                },
                "confidence": 0.88,
                "label_notes": [],
            }
        }
    )
    uow = _FakeGraphUow()
    runtime = MealAnalyzeRuntime(
        command=ScanByUrlCommand(
            user_id="00000000-0000-0000-0000-000000000001",
            image_url=full_url,
            public_id=f"mealtrack/{full_image_id}",
            scan_mode="food_label",
            label_crop_image_url=crop_url,
            label_crop_public_id=f"mealtrack/{crop_image_id}",
        ),
        download_image_bytes=download_image_bytes,
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        uow=uow,
        meal_id_factory=lambda: "22222222-2222-4222-8222-222222222222",
    )

    result = await run_meal_analyze_graph_async(
        {
            "scan_mode": "food_label",
            "image_id": full_image_id,
            "user_id": runtime.command.user_id,
            "target_date": None,
        },
        runtime,
    )

    download_image_bytes.assert_awaited_once_with(crop_url)
    vision_service.analyze_with_strategy.assert_awaited_once()
    meal = result["result"]
    assert meal.image.image_id == full_image_id
    assert meal.image.url == full_url
    assert meal.source == "food_label"


@pytest.mark.asyncio
async def test_async_graph_returns_same_call_locale_without_translation_reload():
    image_id = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value=f"https://res.cloudinary.com/demo/image/upload/mealtrack/{image_id}.jpg"
    )
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "dish_name": "Chicken rice",
                "localized_language": "vi",
                "localized_dish_name": "Cơm gà",
                "confidence": 0.91,
                "foods": [
                    {
                        "name": "Chicken rice",
                        "localized_name": "Cơm gà",
                        "quantity_g": 300,
                        "confidence": 0.91,
                        "macros": {
                            "protein_g": 28,
                            "carbs_g": 52,
                            "fat_g": 8,
                            "fiber_g": 2,
                            "sugar_g": 1,
                        },
                    }
                ],
            }
        }
    )
    cache = AsyncMock()
    cache.enqueue_meal_invalidation = AsyncMock()
    uow = _FakeGraphUow()
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="00000000-0000-0000-0000-000000000001",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
            language="vi",
        ),
        image_store=image_store,
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        uow=uow,
        cache_invalidation=cache,
        image_id_factory=lambda: image_id,
        meal_id_factory=lambda: "22222222-2222-4222-8222-222222222222",
    )

    with patch(
        "src.app.graphs.meal_analyze.nodes.parse_meal_response_localization",
        wraps=parse_meal_response_localization,
    ) as parse_localization:
        result = await run_meal_analyze_graph_async(
            {
                "scan_mode": "meal_scan",
                "user_id": runtime.command.user_id,
                "target_date": None,
            },
            runtime,
        )

    vision_service.analyze.assert_awaited_once_with(
        b"upload-bytes",
        language="vi",
    )
    assert uow.meals.find_by_id.await_count == 0
    cache.enqueue_meal_invalidation.assert_awaited_once()
    assert result["result"].meal_id == "22222222-2222-4222-8222-222222222222"
    assert result["result"].dish_name == "Cơm gà"
    assert result["result"].nutrition.food_items[0].name == "Cơm gà"
    parse_localization.assert_called_once()


@pytest.mark.asyncio
async def test_async_graph_does_not_retry_invalid_localization():
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "foods": [{"name": "Pho", "localized_name": "Phở"}],
            }
        }
    )
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="user-123",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
            language="vi",
        ),
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        max_vision_attempts=3,
    )
    runtime.acquired_image = AcquiredImage(
        image_id="image-123",
        image_url="https://example.com/image-123.jpg",
        persisted_image_id="image-123",
        persisted_image_url="https://example.com/image-123.jpg",
        source_bytes=b"upload-bytes",
        analysis_bytes=b"upload-bytes",
        content_type="image/jpeg",
        content_kind="meal_image",
    )

    with pytest.raises(MealResponseLocalizationError):
        await analyze_vision({}, runtime)

    assert vision_service.analyze.await_count == 1


@pytest.mark.asyncio
async def test_async_graph_treats_malformed_localization_container_as_non_retryable():
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        return_value={
            "structured_data": {
                "is_food": True,
                "foods": 1,
            }
        }
    )
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="user-123",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
            language="vi",
        ),
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        max_vision_attempts=3,
    )
    runtime.acquired_image = AcquiredImage(
        image_id="image-123",
        image_url="https://example.com/image-123.jpg",
        persisted_image_id="image-123",
        persisted_image_url="https://example.com/image-123.jpg",
        source_bytes=b"upload-bytes",
        analysis_bytes=b"upload-bytes",
        content_type="image/jpeg",
        content_kind="meal_image",
    )

    with pytest.raises(MealResponseLocalizationError):
        await analyze_vision({}, runtime)

    assert vision_service.analyze.await_count == 1


@pytest.mark.asyncio
async def test_async_graph_upload_vision_retries_transient_failure():
    image_id = "1325c7ca-e012-4df3-b0b4-55bfaeb55eb0"
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value=f"https://res.cloudinary.com/demo/image/upload/mealtrack/{image_id}.jpg"
    )
    vision_service = AsyncMock()
    vision_service.analyze = AsyncMock(
        side_effect=[
            RuntimeError("temporary vision outage"),
            {
                "structured_data": {
                    "is_food": True,
                    "dish_name": "Chicken rice",
                    "confidence": 0.91,
                    "foods": [
                        {
                            "name": "Chicken rice",
                            "quantity_g": 300,
                            "confidence": 0.91,
                            "macros": {
                                "protein_g": 28,
                                "carbs_g": 52,
                                "fat_g": 8,
                                "fiber_g": 2,
                                "sugar_g": 1,
                            },
                        }
                    ],
                }
            },
        ]
    )
    uow = _FakeGraphUow()
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="00000000-0000-0000-0000-000000000001",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        image_store=image_store,
        vision_service=vision_service,
        gpt_parser=VisionResponseParser(),
        uow=uow,
        image_id_factory=lambda: image_id,
        meal_id_factory=lambda: "22222222-2222-4222-8222-222222222222",
        max_vision_attempts=2,
    )

    result = await run_meal_analyze_graph_async(
        {
            "scan_mode": "meal_scan",
            "user_id": runtime.command.user_id,
            "target_date": None,
        },
        runtime,
    )

    assert vision_service.analyze.await_count == 2
    assert result["result"].meal_id == "22222222-2222-4222-8222-222222222222"


@pytest.mark.asyncio
async def test_acquire_image_upload_saves_bytes_in_runtime_not_state():
    image_store = AsyncMock()
    image_store.save_async = AsyncMock(
        return_value="https://res.cloudinary.com/demo/image/upload/mealtrack/image-123.jpg"
    )
    runtime = MealAnalyzeRuntime(
        command=UploadMealImageImmediatelyCommand(
            user_id="user-123",
            file_contents=b"upload-bytes",
            content_type="image/jpeg",
        ),
        image_store=image_store,
        image_id_factory=lambda: "image-123",
    )

    state_update = await acquire_image({}, runtime)

    image_store.save_async.assert_awaited_once_with(
        b"upload-bytes",
        "image/jpeg",
        "image-123",
    )
    assert state_update == {
        "image_id": "image-123",
        "content_kind": "meal_image",
        "image_size_bytes": len(b"upload-bytes"),
    }
    assert runtime.acquired_image is not None
    assert runtime.acquired_image.image_url.startswith("https://")
    assert runtime.acquired_image.analysis_bytes == b"upload-bytes"
    assert "image_url" not in state_update
    assert "image_bytes" not in state_update


@pytest.mark.asyncio
async def test_acquire_image_scan_by_url_downloads_and_compresses_regular_scan():
    download_image_bytes = AsyncMock(return_value=b"raw-image")
    compression_calls = []

    def compress_image(raw_bytes: bytes) -> bytes:
        compression_calls.append(raw_bytes)
        return b"compressed-image"

    command = ScanByUrlCommand(
        user_id="user-123",
        image_url="https://res.cloudinary.com/demo/image/upload/v1/mealtrack/image-456.jpg",
        public_id="mealtrack/image-456",
        scan_mode="scanner",
    )
    runtime = MealAnalyzeRuntime(
        command=command,
        download_image_bytes=download_image_bytes,
        compress_image=compress_image,
    )

    state_update = await acquire_image({}, runtime)

    download_image_bytes.assert_awaited_once_with(command.image_url)
    assert compression_calls == [b"raw-image"]
    assert state_update == {
        "image_id": "image-456",
        "content_kind": "meal_image",
        "image_size_bytes": len(b"raw-image"),
    }
    assert runtime.acquired_image is not None
    assert runtime.acquired_image.image_url == command.image_url
    assert runtime.acquired_image.analysis_bytes == b"compressed-image"
    assert "image_url" not in state_update
    assert "image_bytes" not in state_update


@pytest.mark.asyncio
async def test_acquire_image_food_label_prefers_crop_without_compression():
    full_url = "https://res.cloudinary.com/demo/image/upload/v1/mealtrack/full.jpg"
    crop_url = "https://res.cloudinary.com/demo/image/upload/v1/mealtrack/crop.jpg"
    download_image_bytes = AsyncMock(
        side_effect=lambda url: {
            full_url: b"full-label-bytes",
            crop_url: b"crop-label-bytes",
        }[url]
    )

    command = ScanByUrlCommand(
        user_id="user-123",
        image_url=full_url,
        public_id="mealtrack/full",
        scan_mode="food_label",
        label_crop_image_url=crop_url,
        label_crop_public_id="mealtrack/crop",
        crop_metadata={"crop_strategy": "food_label_visible_frame_v1"},
    )
    runtime = MealAnalyzeRuntime(
        command=command,
        download_image_bytes=download_image_bytes,
        compress_image=lambda raw_bytes: b"should-not-run",
    )

    state_update = await acquire_image({}, runtime)

    download_image_bytes.assert_awaited_once_with(crop_url)
    assert state_update == {
        "image_id": "crop",
        "content_kind": "food_label_image",
        "image_size_bytes": len(b"crop-label-bytes"),
    }
    assert runtime.acquired_image is not None
    assert runtime.acquired_image.image_url == crop_url
    assert runtime.acquired_image.analysis_bytes == b"crop-label-bytes"
    assert "image_url" not in state_update
    assert "image_bytes" not in state_update
