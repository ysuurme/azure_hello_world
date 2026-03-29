import pytest
from unittest.mock import patch, MagicMock
from src.agents.architecture_composer import ArchitectureComposerAgent

class TestArchitectureComposerAgent:

    @patch('src.agents.architecture_composer.calculate_cost')
    @patch('src.utils.m_ai_client.ClientManager.get_aiproject_client')
    def test_local_composer_generation(self, mock_client, mock_cost):
        """
        Tests the local generation path by bypassing actual LLM connection.
        Verifies that mathematical tools and format drafts still run.
        """
        mock_client.return_value = None
        # Mocking generic calculation value
        mock_cost.return_value = {"trade_off_matrix_data": {"Compute": 100}, "currency": "USD"}
        
        agent = ArchitectureComposerAgent()
        
        test_reqs = {"objective": "Enterprise B2B API", "constraints": "High Availability"}
        result_markdown = agent.generate_architecture(test_reqs)
        
        assert "Enterprise B2B API" in result_markdown
        assert "# Proposed Solution Architecture" in result_markdown
        assert "b. Decisions" in result_markdown
        
    @patch('src.agents.architecture_composer.calculate_cost')
    @patch('src.utils.m_ai_client.ClientManager.get_aiproject_client')
    def test_live_llm_inference_call(self, mock_client, mock_cost):
        """
        Simulates the Azure AI inference payload to ensure structurally correct parsing.
        """
        mock_cost.return_value = {"mock": "cost"}
        
        # Simulate Azure AI response choices
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "## Architecture Output Generated"
        mock_response.choices = [mock_choice]
        
        active_client = MagicMock()
        active_client.inference.get_chat_completions.return_value = mock_response
        mock_client.return_value = active_client
        
        agent = ArchitectureComposerAgent()
        result = agent.generate_architecture({"objective": "Test"})
        
        assert result == "## Architecture Output Generated"
        active_client.inference.get_chat_completions.assert_called_once()
