from unittest.mock import MagicMock

from src.agents.workflow_dispatcher import DispatchResult, WorkflowDispatcher


def _make_dispatcher() -> WorkflowDispatcher:
    cm = MagicMock()
    return WorkflowDispatcher(client_manager=cm)


def _mock_module_response(text: str = "ok", state: dict | None = None, status: str = "completed") -> MagicMock:
    r = MagicMock()
    r.response_text = text
    r.updated_state = state or {}
    r.artifacts = {}
    r.status = status
    return r


class TestCommandParsing:
    def test_unknown_command_returns_unknown_status(self):
        d = _make_dispatcher()
        result = d.dispatch("/unknown some text", {})
        assert result.status == "unknown_command"

    def test_unknown_command_lists_available_commands(self):
        d = _make_dispatcher()
        result = d.dispatch("/bogus", {})
        assert "/diagram" in result.response_text

    def test_known_command_routes_to_module(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(return_value=_mock_module_response("D2 output"))

        result = d.dispatch("/diagram a simple box", {})
        assert result.status == "completed"
        assert result.response_text == "D2 output"

    def test_command_matching_is_case_insensitive(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(return_value=_mock_module_response())

        result = d.dispatch("/DIAGRAM test", {})
        assert result.status == "completed"


class TestSingleModuleHandoff:
    def test_active_module_recorded_in_state(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(return_value=_mock_module_response())

        result = d.dispatch("/diagram test", {})
        assert result.updated_state.get("active_module") == "/diagram"

    def test_module_state_is_namespaced_per_command(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(return_value=_mock_module_response(state={"step": 1}))

        result = d.dispatch("/diagram test", {})
        assert result.updated_state["module_state"]["/diagram"] == {"step": 1}

    def test_prior_session_state_is_preserved(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(return_value=_mock_module_response())

        prior = {"existing_key": "value"}
        result = d.dispatch("/diagram test", prior)
        assert result.updated_state.get("existing_key") == "value"

    def test_return_type_is_dispatch_result(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(return_value=_mock_module_response())

        result = d.dispatch("/diagram test", {})
        assert isinstance(result, DispatchResult)


class TestExceptionIsolation:
    def test_module_exception_returns_error_status(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(side_effect=RuntimeError("boom"))

        result = d.dispatch("/diagram test", {})
        assert result.status == "error"

    def test_module_exception_message_included_in_response(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(side_effect=RuntimeError("boom"))

        result = d.dispatch("/diagram test", {})
        assert "boom" in result.response_text

    def test_module_exception_preserves_session_state(self):
        d = _make_dispatcher()
        d._modules["/diagram"].handle = MagicMock(side_effect=RuntimeError("oops"))

        prior = {"keep": "this"}
        result = d.dispatch("/diagram test", prior)
        assert result.updated_state.get("keep") == "this"
