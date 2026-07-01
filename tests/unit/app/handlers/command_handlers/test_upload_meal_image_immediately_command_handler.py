"""Tests for UploadMealImageImmediatelyHandler — focusing on retry/fallback routing."""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.infra.services.ai.ai_vision_errors import AIVisionError, AIVisionFailureKind


def _make_command():
    from src.app.commands.meal import UploadMealImageImmediatelyCommand

    cmd = Mock(spec=UploadMealImageImmediatelyCommand)
    cmd.file_contents = b"fake_image_bytes"
    cmd.content_type = "image/jpeg"
    cmd.user_id = "00000000-0000-0000-0000-000000000001"
    cmd.user_description = None
    cmd.target_date = None
    cmd.language = None
    cmd.scan_mode = "scanner"
    return cmd


def _make_fast_path_policy(max_attempts: int = 3):
    policy = Mock()
    policy.max_attempts = max_attempts
    return policy


def _make_handler(vision_analyze_mock, max_attempts: int = 3):
    """Build a handler wired with a mocked vision service."""
    from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import (
        UploadMealImageImmediatelyHandler,
    )

    vision_service = Mock()
    vision_service.analyze = vision_analyze_mock
    vision_service.analyze_food_label = AsyncMock()

    handler = UploadMealImageImmediatelyHandler(
        uow=Mock(),
        event_bus=Mock(),
        image_store=Mock(),
        vision_service=vision_service,
        gpt_parser=Mock(),
        meal_translation_service=None,
        fast_path_policy=_make_fast_path_policy(max_attempts),
        cache_invalidation=None,
    )
    return handler


def _make_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.users = MagicMock()
    uow.users.get_user_timezone = AsyncMock(return_value="UTC")
    uow.meals = MagicMock()
    uow.meals.save = AsyncMock(side_effect=lambda meal: meal)
    uow.commit = AsyncMock()
    return uow


class TestVisionRetryRouting:
    """Phase 3: upload handler skips outer retry for deterministic vision failures."""

    @pytest.mark.asyncio
    async def test_vision_schema_fail_does_not_outer_retry(self):
        """Schema validation failure is raised immediately — analyze called exactly once."""
        schema_error = AIVisionError(
            "[CF-WORKERS-AI-VISION-SCHEMA-FAIL] provider=cloudflare-workers-ai model=test",
            kind=AIVisionFailureKind.schema_validation,
            provider="cloudflare-workers-ai",
            model="test",
        )
        analyze_mock = AsyncMock(side_effect=schema_error)
        handler = _make_handler(analyze_mock, max_attempts=3)

        with pytest.raises(AIVisionError) as exc_info:
            await handler._run_vision_analysis(_make_command(), meal_id="meal-abc")

        assert exc_info.value.kind == AIVisionFailureKind.schema_validation
        # Only called once — no outer retry attempted
        analyze_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_vision_json_parse_fail_does_not_outer_retry(self):
        """JSON parse failure is raised immediately — analyze called exactly once."""
        parse_error = AIVisionError(
            "[CF-WORKERS-AI-VISION-PARSE-FAIL] provider=cloudflare-workers-ai model=test",
            kind=AIVisionFailureKind.json_parse,
            provider="cloudflare-workers-ai",
            model="test",
        )
        analyze_mock = AsyncMock(side_effect=parse_error)
        handler = _make_handler(analyze_mock, max_attempts=3)

        with pytest.raises(AIVisionError) as exc_info:
            await handler._run_vision_analysis(_make_command(), meal_id="meal-abc")

        assert exc_info.value.kind == AIVisionFailureKind.json_parse
        analyze_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_vision_no_food_fail_does_not_outer_retry(self):
        """no_food failure is raised immediately — analyze called exactly once."""
        no_food_error = AIVisionError(
            "No food detected",
            kind=AIVisionFailureKind.no_food,
            provider="openai",
            model="gpt-5.4-mini-2026-03-17",
        )
        analyze_mock = AsyncMock(side_effect=no_food_error)
        handler = _make_handler(analyze_mock, max_attempts=3)

        with pytest.raises(AIVisionError) as exc_info:
            await handler._run_vision_analysis(_make_command(), meal_id="meal-abc")

        assert exc_info.value.kind == AIVisionFailureKind.no_food
        analyze_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_vision_transient_fail_triggers_outer_retry(self):
        """Plain Exception (transient) causes outer retry — analyze called twice when first fails."""
        analysis_result = {"food_items": [{"name": "apple"}]}
        analyze_mock = AsyncMock(
            side_effect=[Exception("503 Service Unavailable"), analysis_result]
        )
        handler = _make_handler(analyze_mock, max_attempts=3)

        result = await handler._run_vision_analysis(_make_command(), meal_id="meal-abc")

        assert result == analysis_result
        assert analyze_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_vision_transient_fail_exhausts_max_attempts_and_raises(self):
        """Transient failure on all attempts raises the last exception after max_attempts."""
        analyze_mock = AsyncMock(side_effect=Exception("persistent 503"))
        handler = _make_handler(analyze_mock, max_attempts=2)

        with pytest.raises(Exception, match="persistent 503"):
            await handler._run_vision_analysis(_make_command(), meal_id="meal-abc")

        assert analyze_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_food_label_mode_uses_label_analyzer(self):
        """Food-label scans route through the label-specific analyzer."""
        analyze_mock = AsyncMock()
        handler = _make_handler(analyze_mock, max_attempts=3)
        command = _make_command()
        command.scan_mode = "food_label"
        handler.vision_service.analyze_food_label = AsyncMock(
            return_value={"is_food_label": True}
        )

        result = await handler._run_vision_analysis(command, meal_id="meal-abc")

        assert result == {"is_food_label": True}
        handler.vision_service.analyze_food_label.assert_awaited_once_with(
            command.file_contents
        )
        analyze_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_food_label_parallel_upload_persists_ready_label_meal(self):
        from src.app.handlers.command_handlers.upload_meal_image_immediately_command_handler import (
            UploadMealImageImmediatelyHandler,
        )
        from src.domain.model.nutrition import FoodItem, Macros, Nutrition

        command = _make_command()
        command.scan_mode = "food_label"
        uow = _make_uow()
        image_store = Mock()
        image_store.save_async = AsyncMock(return_value="https://cdn.test/label.jpg")
        vision_service = Mock()
        vision_service.analyze_food_label = AsyncMock(
            return_value={"is_food_label": True, "product_name": "Protein Bar"}
        )
        parser = Mock()
        parser.parse_food_label_to_nutrition.return_value = Nutrition(
            macros=Macros(protein=10, carbs=20, fat=5, fiber=4, sugar=8),
            food_items=[
                FoodItem(
                    id="label-item",
                    name="Protein Bar",
                    quantity=55,
                    unit="g",
                    macros=Macros(protein=10, carbs=20, fat=5, fiber=4, sugar=8),
                    is_custom=True,
                )
            ],
        )
        label_metadata = {
            "is_food_label": True,
            "product_name": "Protein Bar",
            "serving_size": {"display_text": "1 bar (55g)", "grams": 55},
            "servings_per_package": 8,
            "confidence": 0.92,
        }
        parser.parse_food_label_metadata.return_value = label_metadata
        parser.extract_raw_json.return_value = '{"product_name":"Protein Bar"}'
        parser.parse_is_food = Mock()
        cache = Mock()
        cache.after_meal_write = AsyncMock()

        handler = UploadMealImageImmediatelyHandler(
            uow=uow,
            event_bus=Mock(),
            image_store=image_store,
            vision_service=vision_service,
            gpt_parser=parser,
            fast_path_policy=_make_fast_path_policy(),
            cache_invalidation=cache,
        )

        meal = await handler._handle_parallel_upload(command)

        assert meal.status.value == "READY"
        assert meal.source == "food_label"
        assert meal.dish_name == "Unnamed Food"
        assert meal.emoji is None
        assert meal.food_label_metadata == label_metadata
        assert meal.nutrition.food_items[0].quantity == 55
        uow.meals.save.assert_awaited_once()
        saved_meal = uow.meals.save.await_args.args[0]
        assert saved_meal.food_label_metadata == label_metadata
        cache.after_meal_write.assert_awaited_once()
        parser.parse_is_food.assert_not_called()
        parser.parse_food_label_name.assert_not_called()
