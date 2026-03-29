import pytest
from unittest.mock import patch
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.utils.m_ai_client import ClientManager

class TestIntakeReviewerAgent:
    
    @patch('src.utils.m_ai_client.ClientManager.get_chat_completions_client')
    def test_mocked_insufficient_prompt(self, mock_chat_client):
        """Verify that the agent calls the live chat client and parses a 'needs_clarification' response."""
        # Simulate chat client returning a JSON payload indicating clarification needed
        mock_response = type("R", (), {})()
        mock_choice = type("C", (), {})()
        mock_choice.message = type("M", (), {"content": '{"status": "needs_clarification", "questions": ["Please provide more details on workload."]}'})
        mock_response.choices = [mock_choice]

        mock_chat = type("Chat", (), {"complete": lambda *args, **kwargs: mock_response})
        mock_chat_client.return_value = mock_chat()

        agent = IntakeReviewerAgent(client_manager=ClientManager())
        response = agent.review_input("App")
        assert response.get("status") == "needs_clarification"
        assert "questions" in response

    @patch('src.utils.m_ai_client.ClientManager.get_chat_completions_client')
    def test_mocked_sufficient_prompt(self, mock_chat_client):
        """Verify that the agent calls the live chat client and parses a 'ready' response."""
        mock_response = type("R", (), {})()
        mock_choice = type("C", (), {})()
        mock_choice.message = type("M", (), {"content": '{"status": "ready", "requirements": {"objective": "..."}}'})
        mock_response.choices = [mock_choice]

        mock_chat = type("Chat", (), {"complete": lambda *args, **kwargs: mock_response})
        mock_chat_client.return_value = mock_chat()

        agent = IntakeReviewerAgent(client_manager=ClientManager())
        valid_prompt = "I need a highly available B2B SaaS architecture using relational databases for financial data under a budget."
        response = agent.review_input(valid_prompt)
        assert response.get("status") == "ready"
        assert "requirements" in response
