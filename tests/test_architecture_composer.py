import pytest
from unittest.mock import patch, MagicMock
from src.agents.architecture_composer import ArchitectureComposerAgent
from src.utils.m_ai_client import ClientManager

class TestArchitectureComposerAgent:

    @patch('src.agents.architecture_composer.calculate_cost')
    @patch('src.utils.m_ai_client.ClientManager.get_chat_completions_client')
    def test_local_composer_generation(self, mock_chat_client, mock_cost):
        """
        Tests the local generation path by bypassing actual LLM connection.
        Verifies that mathematical tools and format drafts still run.
        """
        # Mocking generic calculation value
        mock_cost.return_value = {"trade_off_matrix_data": {"Compute": 100}, "currency": "USD"}

        # Provide a mock chat client that returns a markdown containing expected fragments
        class MockChat:
            def complete(self, *args, **kwargs):
                class Choice:
                    class Message:
                        content = "# Proposed Solution Architecture\n\n## a. Purpose\nTo fulfill the business objective: Enterprise B2B API\n\n## b. Decisions"
                    message = Message()
                class Resp:
                    choices = [Choice()]
                return Resp()

        mock_chat_client.return_value = MockChat()

        agent = ArchitectureComposerAgent(client_manager=ClientManager())

        test_reqs = {"objective": "Enterprise B2B API", "constraints": "High Availability"}
        result_markdown = agent.generate_architecture(test_reqs)

        assert "Enterprise B2B API" in result_markdown
        assert "# Proposed Solution Architecture" in result_markdown
        assert "b. Decisions" in result_markdown
        
    @patch('src.agents.architecture_composer.calculate_cost')
    @patch('src.utils.m_ai_client.ClientManager.get_chat_completions_client')
    def test_live_llm_inference_call(self, mock_chat_client, mock_cost):
        """
        Simulates the Azure AI inference payload to ensure structurally correct parsing.
        """
        mock_cost.return_value = {"mock": "cost"}
        
        # Simulate Azure AI response choices
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "## Architecture Output Generated"
        mock_response.choices = [mock_choice]
        
        # Make a mock chat client whose complete() returns the mock_response
        mock_chat = MagicMock()
        mock_chat.complete.return_value = mock_response

        mock_chat_client.return_value = mock_chat

        agent = ArchitectureComposerAgent(client_manager=ClientManager())
        result = agent.generate_architecture({"objective": "Test"})

        assert result == "## Architecture Output Generated"
        mock_chat.complete.assert_called_once()
