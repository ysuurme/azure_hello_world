import pytest
from unittest.mock import patch
from src.agents.intake_reviewer import IntakeReviewerAgent

class TestIntakeReviewerAgent:
    
    @patch('src.agents.intake_reviewer.get_foundry_agent_client')
    def test_mocked_insufficient_prompt(self, mock_client):
        """
        Verify that a prompt with fewer than 5 words natively triggers the clarification status.
        Follows 'Single Responsibility' testing.
        """
        mock_client.return_value = None
        agent = IntakeReviewerAgent()
        
        response = agent.review_input("App")
        
        assert response.get("status") == "needs_clarification"
        assert "questions" in response

    @patch('src.agents.intake_reviewer.get_foundry_agent_client')
    def test_mocked_sufficient_prompt(self, mock_client):
        """
        Verify that a long, descriptive prompt natively triggers a ready state constraint dict.
        """
        mock_client.return_value = None
        agent = IntakeReviewerAgent()
        
        valid_prompt = "I need a highly available B2B SaaS architecture using relational databases for financial data under a budget."
        response = agent.review_input(valid_prompt)
        
        assert response.get("status") == "ready"
        assert "requirements" in response
