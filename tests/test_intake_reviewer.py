import pytest
from unittest.mock import patch
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.utils.m_ai_client import ClientManager

class TestIntakeReviewerAgent:
    
    @patch('src.utils.m_ai_client.ClientManager.get_openai_client')
    def test_mocked_insufficient_prompt(self, mock_openai_cm):
        """Verify that the agent calls the live chat client and parses a 'needs_clarification' response."""
        # Simulate chat client returning a JSON payload indicating clarification needed
        mock_response = type("R", (), {})()
        mock_choice = type("C", (), {})()
        mock_choice.message = type("M", (), {"content": '{"status": "needs_clarification", "questions": ["Please provide more details on workload."]}'})
        mock_response.choices = [mock_choice]

        # Build context manager that returns an object with responses.create returning raw json
        class CM:
            def __enter__(self):
                class O:
                    def __init__(self):
                        class Responses:
                            def create(self, model, input):
                                return type("Resp", (), {"output_text": mock_choice.message.content})()
                        self.responses = Responses()
                return O()
            def __exit__(self, exc_type, exc, tb):
                return False
        mock_openai_cm.return_value = CM()

        agent = IntakeReviewerAgent(client_manager=ClientManager())
        response = agent.review_input("App")
        assert response.get("status") == "needs_clarification"
        assert "questions" in response

    @patch('src.utils.m_ai_client.ClientManager.get_openai_client')
    def test_mocked_sufficient_prompt(self, mock_openai_cm):
        """Verify that the agent calls the live chat client and parses a 'ready' response."""
        mock_response = type("R", (), {})()
        mock_choice = type("C", (), {})()
        mock_choice.message = type("M", (), {"content": '{"status": "ready", "requirements": {"objective": "..."}}'})
        mock_response.choices = [mock_choice]

        class CM2:
            def __enter__(self):
                class O:
                    def __init__(self):
                        class Responses:
                            def create(self, model, input):
                                return type("Resp", (), {"output_text": mock_choice.message.content})()
                        self.responses = Responses()
                return O()
            def __exit__(self, exc_type, exc, tb):
                return False
        mock_openai_cm.return_value = CM2()

        agent = IntakeReviewerAgent(client_manager=ClientManager())
        valid_prompt = "I need a highly available B2B SaaS architecture using relational databases for financial data under a budget."
        response = agent.review_input(valid_prompt)
        assert response.get("status") == "ready"
        assert "requirements" in response
