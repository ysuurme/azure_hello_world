"""Tests for src/ui/app.py — Streamlit frontend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest


def _mock_backend_response(
    text: str = "Mocked response",
    state: dict | None = None,
    status: str = "completed",
) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "response_text": text,
        "updated_state": state or {},
        "artifacts": {"svg": None, "d2": None},
        "status": status,
    }
    return resp


class TestUITopology:
    @pytest.fixture
    def app_test(self):
        """Initializes the Streamlit AppTest framework for headless UI validation."""
        return AppTest.from_file("src/ui/app.py")

    def test_app_instantiation_and_layout(self, app_test) -> None:
        """Verify the app loads without structural errors and shows expected layout."""
        app_test.run(timeout=10)

        assert not app_test.exception

        assert app_test.title[0].value == "Architecture Agent 🛡️"
        assert app_test.markdown[0].value == "### Technical Design Authority Agent"

        assert "Backend:" in app_test.sidebar.info[0].value

    def test_app_session_reset(self, app_test) -> None:
        """Verify the reset button properly restores session history bounds."""
        app_test.run(timeout=10)
        assert len(app_test.session_state["chat_history"]) == 1

        with patch("requests.post", return_value=_mock_backend_response()):
            app_test.chat_input[0].set_value("Analyze App Service").run()

        assert len(app_test.session_state["chat_history"]) > 1

        app_test.sidebar.button[0].click().run()

        assert len(app_test.session_state["chat_history"]) == 1

    def test_no_slash_input_posts_to_backend(self, app_test) -> None:
        """User input must be POSTed to the backend /dispatch endpoint."""
        mock_resp = _mock_backend_response(text="Help text", status="unknown_command")

        app_test.run(timeout=10)
        with patch("requests.post", return_value=mock_resp) as mock_post:
            app_test.chat_input[0].set_value("plain text no slash").run()

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/dispatch" in call_args.args[0]
        assert call_args.kwargs["json"]["query"] == "plain text no slash"
