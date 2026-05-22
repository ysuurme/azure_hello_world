from unittest.mock import MagicMock, patch

from src.agents.workflow_dispatcher import DispatchResult, WorkflowDispatcher


def _make_dispatcher() -> WorkflowDispatcher:
    return WorkflowDispatcher(client_manager=MagicMock())


def _set_intake_ready(mock_reviewer_cls) -> None:
    mock_reviewer_cls.return_value.review_input.return_value = {
        "status": "ready",
        "requirements": {"objective": "Test"},
    }


def _set_intake_clarify(mock_reviewer_cls, questions: list[str] | None = None) -> None:
    mock_reviewer_cls.return_value.review_input.return_value = {
        "status": "needs_clarification",
        "questions": questions or ["What region?"],
    }


# Contract change (#43): tests now mock IntakeReviewerAgent / ArchitectureComposerAgent directly
# since AgenticOrchestrator was folded into DesignArchitectureModule.
class TestDesignArchitectureViaDispatcher:
    @patch("src.agents.design_architecture.IntakeReviewerAgent")
    @patch("src.agents.design_architecture.ArchitectureComposerAgent")
    @patch("src.agents.design_architecture.ArchitecturePersister")
    def test_design_command_routes_to_module(self, _persister, mock_composer, mock_reviewer):
        _set_intake_ready(mock_reviewer)
        mock_composer.return_value.generate_architecture.return_value = "## Architecture Created"
        mock_composer.return_value.generate_d2_syntax.return_value = None

        d = _make_dispatcher()
        result = d.dispatch("/design a multi-region web app on Azure", {})

        assert isinstance(result, DispatchResult)
        assert result.status == "completed"
        assert "Architecture Created" in result.response_text

    @patch("src.agents.design_architecture.IntakeReviewerAgent")
    @patch("src.agents.design_architecture.ArchitectureComposerAgent")
    def test_design_command_clarifying_phase_returns_in_refinement(self, _composer, mock_reviewer):
        _set_intake_clarify(mock_reviewer)

        d = _make_dispatcher()
        result = d.dispatch("/design build something", {})

        assert result.status == "in_refinement"
        assert "clarify" in result.response_text

    @patch("src.agents.design_architecture.IntakeReviewerAgent")
    @patch("src.agents.design_architecture.ArchitectureComposerAgent")
    def test_design_active_module_recorded_in_state(self, _composer, mock_reviewer):
        _set_intake_clarify(mock_reviewer)

        d = _make_dispatcher()
        result = d.dispatch("/design build something", {})

        assert result.updated_state.get("active_module") == "/design"

    @patch("src.agents.design_architecture.IntakeReviewerAgent")
    @patch("src.agents.design_architecture.ArchitectureComposerAgent")
    @patch("src.agents.design_architecture.ArchitecturePersister")
    def test_design_intake_receives_prompt_without_slash_command(self, _persister, mock_composer, mock_reviewer):
        _set_intake_ready(mock_reviewer)
        mock_composer.return_value.generate_architecture.return_value = "## Done"
        mock_composer.return_value.generate_d2_syntax.return_value = None

        d = _make_dispatcher()
        d.dispatch("/design build a web app", {})

        call_args = mock_reviewer.return_value.review_input.call_args[0]
        assert call_args[0] == "build a web app"

    @patch("src.agents.design_architecture.IntakeReviewerAgent")
    @patch("src.agents.design_architecture.ArchitectureComposerAgent")
    @patch("src.agents.design_architecture.ArchitecturePersister")
    def test_design_generation_phase_persists_architecture(self, mock_persister, mock_composer, mock_reviewer):
        _set_intake_ready(mock_reviewer)
        mock_composer.return_value.generate_architecture.return_value = "## Architecture"
        mock_composer.return_value.generate_d2_syntax.return_value = None

        d = _make_dispatcher()
        d.dispatch("/design build something", {})

        mock_persister.return_value.archive_solution.assert_called_once()

    @patch("src.agents.design_architecture.IntakeReviewerAgent")
    @patch("src.agents.design_architecture.ArchitectureComposerAgent")
    @patch("src.agents.design_architecture.ArchitecturePersister")
    @patch("src.agents.design_architecture.DiagramEngine")
    def test_design_generation_phase_with_d2_produces_svg_artifact(
        self, mock_engine, _persister, mock_composer, mock_reviewer
    ):
        _set_intake_ready(mock_reviewer)
        mock_composer.return_value.generate_architecture.return_value = "## Architecture\n```d2\n...\n```"
        mock_composer.return_value.generate_d2_syntax.return_value = "direction: right\nA -> B"
        mock_engine.return_value.generate_svg.return_value = b"<svg/>"

        d = _make_dispatcher()
        result = d.dispatch("/design build something", {})

        assert result.artifacts.get("svg") == b"<svg/>"
        assert result.artifacts.get("d2") == "direction: right\nA -> B"
