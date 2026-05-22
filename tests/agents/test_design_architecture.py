from unittest.mock import MagicMock, patch

from src.agents.workflow_dispatcher import DispatchResult, WorkflowDispatcher


def _make_dispatcher() -> WorkflowDispatcher:
    return WorkflowDispatcher(client_manager=MagicMock())


class TestDesignArchitectureViaDispatcher:
    @patch("src.agents.design_architecture.AgenticOrchestrator")
    def test_design_command_routes_to_module(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.orchestrate_cycle.return_value = ({"phase": "GENERATION"}, "## Architecture Created")
        mock_orch.get_d2_syntax.return_value = None

        d = _make_dispatcher()
        with patch("src.agents.design_architecture.ArchitecturePersister"):
            result = d.dispatch("/design a multi-region web app on Azure", {})

        assert isinstance(result, DispatchResult)
        assert result.status == "completed"
        assert "Architecture Created" in result.response_text

    @patch("src.agents.design_architecture.AgenticOrchestrator")
    def test_design_command_clarifying_phase_returns_in_refinement(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.orchestrate_cycle.return_value = (
            {"phase": "CLARIFYING"},
            "To help me design this architecture perfectly, please clarify:\n- What region?",
        )

        d = _make_dispatcher()
        result = d.dispatch("/design build something", {})

        assert result.status == "in_refinement"
        assert "clarify" in result.response_text

    @patch("src.agents.design_architecture.AgenticOrchestrator")
    def test_design_active_module_recorded_in_state(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.orchestrate_cycle.return_value = ({"phase": "CLARIFYING"}, "Questions...")

        d = _make_dispatcher()
        result = d.dispatch("/design build something", {})

        assert result.updated_state.get("active_module") == "/design"

    @patch("src.agents.design_architecture.AgenticOrchestrator")
    def test_design_orchestrator_receives_prompt_without_slash_command(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.orchestrate_cycle.return_value = ({"phase": "GENERATION"}, "## Done")
        mock_orch.get_d2_syntax.return_value = None

        d = _make_dispatcher()
        with patch("src.agents.design_architecture.ArchitecturePersister"):
            d.dispatch("/design build a web app", {})

        call_args = mock_orch.orchestrate_cycle.call_args[0]
        assert call_args[0] == "build a web app"

    @patch("src.agents.design_architecture.AgenticOrchestrator")
    def test_design_generation_phase_persists_architecture(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.orchestrate_cycle.return_value = ({"phase": "GENERATION"}, "## Architecture")
        mock_orch.get_d2_syntax.return_value = None

        d = _make_dispatcher()
        with patch("src.agents.design_architecture.ArchitecturePersister") as mock_persister_cls:
            d.dispatch("/design build something", {})

        mock_persister_cls.return_value.archive_solution.assert_called_once()

    @patch("src.agents.design_architecture.AgenticOrchestrator")
    def test_design_generation_phase_with_d2_produces_svg_artifact(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.orchestrate_cycle.return_value = ({"phase": "GENERATION"}, "## Architecture\n```d2\n...\n```")
        mock_orch.get_d2_syntax.return_value = "direction: right\nA -> B"

        d = _make_dispatcher()
        with patch("src.agents.design_architecture.DiagramEngine") as mock_engine_cls:
            with patch("src.agents.design_architecture.ArchitecturePersister"):
                mock_engine_cls.return_value.generate_svg.return_value = b"<svg/>"
                result = d.dispatch("/design build something", {})

        assert result.artifacts.get("svg") == b"<svg/>"
        assert result.artifacts.get("d2") == "direction: right\nA -> B"
