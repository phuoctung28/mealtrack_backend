from unittest.mock import MagicMock, patch

from src.infra.adapters.vision_ai_service import VisionAIService

_MGR_PATCH = "src.infra.adapters.vision_ai_service.GeminiModelManager"


def test_vision_service_disables_thinking_and_caps_output():
    with patch(_MGR_PATCH) as mock_cls:
        mock_mgr = MagicMock()
        mock_cls.get_instance.return_value = mock_mgr

        VisionAIService()

        mock_cls.get_instance.assert_called_once()
        mock_mgr.get_model.assert_called_once_with(
            thinking_budget=0, max_output_tokens=1024
        )
