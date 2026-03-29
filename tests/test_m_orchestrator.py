import pytest
from unittest.mock import patch, MagicMock
from src.utils.m_orchestrator import AgenticOrchestrator
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.agents.architecture_composer import ArchitectureComposerAgent

class TestAgenticOrchestrator:

    @patch('src.utils.m_orchestrator.IntakeReviewerAgent')
    @patch('src.utils.m_orchestrator.ArchitectureComposerAgent')
    def test_orchestrator_initial_state(self, mock_composer, mock_reviewer):
        """
        Ensures the Orchestrator safely instantiates its two sub-agents.
        """
        orchestrator = AgenticOrchestrator()
        
        # It assigns class instances dynamically internally
        assert orchestrator.reviewer is not None
        assert orchestrator.composer is not None

    @patch('src.utils.m_orchestrator.IntakeReviewerAgent')
    @patch('src.utils.m_orchestrator.ArchitectureComposerAgent')
    def test_orchestrator_state_transition(self, mock_composer, mock_reviewer):
        """
        Ensure state dictionary shifts from INTAKE to GENERATION when requirements are fully satisfied.
        """
        mock_reviewer_instance = mock_reviewer.return_value
        mock_reviewer_instance.review_input.return_value = {
            "status": "ready",
            "requirements": {"objective": "Test System"}
        }
        
        mock_composer_instance = mock_composer.return_value
        mock_composer_instance.generate_architecture.return_value = "## Architecture Created"
        
        orchestrator = AgenticOrchestrator()
        
        initial_state = {"phase": "INTAKE"}
        updated_state, response_text = orchestrator.orchestrate_cycle("Create an app.", initial_state)
        
        # Validates phase transitioned
        assert updated_state["phase"] == 'GENERATION'
        assert "Architecture Created" in response_text
