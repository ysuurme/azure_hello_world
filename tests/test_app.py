import pytest
from streamlit.testing.v1 import AppTest


class TestUITopology:
    @pytest.fixture
    def app_test(self):
        """Initializes the Streamlit AppTest framework for Headless UI validation."""
        from unittest.mock import MagicMock, patch

        mock_result = MagicMock()
        mock_result.response_text = "Mocked response"
        mock_result.updated_state = {}
        mock_result.artifacts = {}
        mock_result.status = "completed"

        with patch("src.agents.workflow_dispatcher.WorkflowDispatcher.dispatch", return_value=mock_result):
            at = AppTest.from_file("src/ui/app.py")
            yield at

    def test_app_instantiation_and_layout(self, app_test):
        """
        Verify that the Streamlit application Native MVP loads without structural HTTP dependency errors.
        Ensures the sidebar and primary titles are properly configured.
        """
        app_test.run(timeout=10)

        assert not app_test.exception

        assert app_test.title[0].value == "Architecture Agent 🛡️"
        assert app_test.markdown[0].value == "### Technical Design Authority Agent"

        assert app_test.sidebar.info[0].value == "Running Lean MVP locally. All input routed via WorkflowDispatcher."

    def test_app_session_reset(self, app_test):
        """
        Verify the reset button properly restores session history bounds.
        """
        app_test.run(timeout=10)
        assert len(app_test.session_state["chat_history"]) == 1

        app_test.chat_input[0].set_value("Analyze App Service").run()

        assert len(app_test.session_state["chat_history"]) > 1

        app_test.sidebar.button[0].click().run()

        assert len(app_test.session_state["chat_history"]) == 1

    def test_no_slash_input_routes_through_dispatcher(self, app_test):
        """No-slash input must go through WorkflowDispatcher, not AgenticOrchestrator."""
        from unittest.mock import MagicMock, patch

        mock_result = MagicMock()
        mock_result.response_text = "Help text"
        mock_result.updated_state = {}
        mock_result.artifacts = {}
        mock_result.status = "unknown_command"

        _target = "src.agents.workflow_dispatcher.WorkflowDispatcher.dispatch"
        app_test.run(timeout=10)
        with patch(_target, return_value=mock_result) as mock_dispatch:
            app_test.chat_input[0].set_value("plain text no slash").run()
            mock_dispatch.assert_called_once()
            call_args = mock_dispatch.call_args[0]
            assert call_args[0] == "plain text no slash"
