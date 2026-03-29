import os
import json
from unittest import mock

import pytest

from src.utils.m_ai_client import ClientManager
from src.agents.architecture_composer import ArchitectureComposerAgent
from src.agents.intake_reviewer import IntakeReviewerAgent

# Helper mock for AIProjectClient
class MockAIProjectClient:
    def __init__(self, *args, **kwargs):
        pass

    class inference:
        @staticmethod
        def get_chat_completions(*, model, messages):
            # Return a simple mock response structure
            class Choice:
                class Message:
                    content = "Mocked architecture response"
                message = Message()
            class Response:
                choices = [Choice()]
            return Response()


def test_get_foundry_client_with_raw_endpoint(monkeypatch):
    """Validate that a raw endpoint string is parsed correctly and a client is created."""
    monkeypatch.setenv("AZURE_AAIF_PROJECT_ENDPOINT", "endpoint=https://example.com")
    # Patch the Azure SDK classes to avoid real network calls
    monkeypatch.setattr("azure.ai.projects.AIProjectClient", MockAIProjectClient)
    monkeypatch.setattr("azure.identity.DefaultAzureCredential", lambda: None)

    client = ClientManager().get_aiproject_client()
    assert isinstance(client, MockAIProjectClient)


def test_get_foundry_client_missing(monkeypatch):
    """When no connection string is present the factory should return None."""
    monkeypatch.delenv("AZURE_AAIF_PROJECT_ENDPOINT", raising=False)
    client = ClientManager().get_aiproject_client()
    assert client is None


def test_architecture_composer_fallback(monkeypatch):
    """When no client is available the composer should return mocked markdown."""
    monkeypatch.setattr("src.utils.m_ai_client.ClientManager.get_aiproject_client", lambda self: None)
    agent = ArchitectureComposerAgent()
    req = {"objective": "Demo app"}
    result = agent.generate_architecture(req)
    assert "# Proposed Solution Architecture" in result
    assert "## a. Purpose" in result


def test_intake_reviewer_fallback(monkeypatch):
    """When no client is available the intake reviewer should return a mocked dict."""
    monkeypatch.setattr("src.utils.m_ai_client.ClientManager.get_aiproject_client", lambda self: None)
    reviewer = IntakeReviewerAgent()
    short_prompt = "short"
    result = reviewer.review_input(short_prompt)
    # With less than 5 words it should request clarification
    assert result["status"] == "needs_clarification"
    long_prompt = "This is a sufficiently long prompt describing the workload and constraints"
    result = reviewer.review_input(long_prompt)
    assert result["status"] == "ready"
    assert isinstance(result["requirements"], dict)
