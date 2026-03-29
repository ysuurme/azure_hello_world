import os
import json
from unittest import mock

import pytest

from src.utils.m_ai_client import ClientManager
from src.agents.architecture_composer import ArchitectureComposerAgent
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.utils.m_ai_client import ClientManager

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
    with pytest.raises(RuntimeError):
        ClientManager().get_aiproject_client()


def test_architecture_composer_fallback(monkeypatch):
    """When a chat client is available the composer should use it to generate markdown."""
    # Provide a mock chat client exposing `complete(...)` returning a response object
    class MockChat:
        def complete(self, *args, **kwargs):
            class Choice:
                class Message:
                    content = "# Proposed Solution Architecture\n\n## a. Purpose\nMocked"
                message = Message()
            class Resp:
                choices = [Choice()]
            return Resp()

    # Patch the ClientManager to return a context manager exposing `responses.create`
    class MockOpenAI:
        def __enter__(self):
            class C:
                def __init__(self):
                    class Responses:
                        def create(self, model, input):
                            class Resp:
                                output_text = "# Proposed Solution Architecture\n\n## a. Purpose\nMocked"
                            return Resp()
                    self.responses = Responses()
            return C()
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("src.utils.m_ai_client.ClientManager.get_openai_client", lambda self: MockOpenAI())
    agent = ArchitectureComposerAgent(client_manager=ClientManager())
    req = {"objective": "Demo app"}
    result = agent.generate_architecture(req)
    assert "# Proposed Solution Architecture" in result
    assert "## a. Purpose" in result


def test_intake_reviewer_fallback(monkeypatch):
    """When a chat client is available the intake reviewer should parse chat responses."""
    # Mock chat responses for short and long prompts
    def make_chat_with(content):
        class MockChat:
            def complete(self, *args, **kwargs):
                class Choice:
                    class Message:
                        pass
                    message = Message()
                class Resp:
                    pass
                mock_choice = Choice()
                mock_choice.message.content = content
                resp = Resp()
                resp.choices = [mock_choice]
                return resp
        return MockChat()

    short_json = '{"status": "needs_clarification", "questions": ["Please provide more details on workload."]}'
    long_json = '{"status": "ready", "requirements": {"objective": "Demo"}}'

    # First test short prompt
    monkeypatch.setattr("src.utils.m_ai_client.ClientManager.get_openai_client", lambda self: type("CM", (), {"__enter__": lambda s: type("O", (), {"responses": type("R", (), {"create": lambda self, model, input: type("Resp", (), {"output_text": short_json})()})()}), "__exit__": lambda s, a, b, c: False})())
    reviewer = IntakeReviewerAgent(client_manager=ClientManager())
    short_prompt = "short"
    result = reviewer.review_input(short_prompt)
    assert result["status"] == "needs_clarification"

    # Then test long prompt
    monkeypatch.setattr("src.utils.m_ai_client.ClientManager.get_openai_client", lambda self: type("CM", (), {"__enter__": lambda s: type("O", (), {"responses": type("R", (), {"create": lambda self, model, input: type("Resp", (), {"output_text": long_json})()})()}), "__exit__": lambda s, a, b, c: False})())
    reviewer = IntakeReviewerAgent(client_manager=ClientManager())
    long_prompt = "This is a sufficiently long prompt describing the workload and constraints"
    result = reviewer.review_input(long_prompt)
    assert result["status"] == "ready"
    assert isinstance(result.get("requirements"), dict)
