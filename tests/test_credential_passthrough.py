
from unittest.mock import MagicMock, patch

import pytest

import src.utils.m_ai_client as m_ai_client
from src.agents.architecture_composer import ArchitectureComposerAgent
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.utils.m_ai_client import ClientManager


@pytest.fixture(autouse=True)
def reset_global_cache():
    """Reset the global AIProjectClient cache between tests."""
    m_ai_client._cached_aiproject_client = None
    yield
    m_ai_client._cached_aiproject_client = None

def test_client_manager_single_credential_source():
    """Verify that ClientManager uses a single credential source and passes it to clients."""
    with patch("azure.identity.DefaultAzureCredential") as mock_cred_cls:
        mock_cred_instance = MagicMock()
        mock_cred_cls.return_value = mock_cred_instance
        
        cm = ClientManager()
        
        # First call to get_credential should create it
        cred1 = cm.get_credential()
        assert cred1 == mock_cred_instance
        mock_cred_cls.assert_called_once()
        
        # Second call should return the same instance due to caching
        cred2 = cm.get_credential()
        assert cred2 == mock_cred_instance
        mock_cred_cls.assert_called_once()

def test_credential_passthrough_to_aiproject_client_endpoint(monkeypatch):
    """Verify that the credential from ClientManager is passed to AIProjectClient (endpoint style)."""
    monkeypatch.setenv("AZURE_AAIF_PROJECT_ENDPOINT", "endpoint=https://test.endpoint")
    
    with patch("src.utils.m_ai_client._AuthManager.get_azure_credential") as mock_get_cred:
        mock_cred = MagicMock()
        mock_get_cred.return_value = mock_cred
        
        # Patch AIProjectClient where it is USED in src.utils.m_ai_client
        with patch("src.utils.m_ai_client.projects.AIProjectClient") as mock_ai_client_cls:
            cm = ClientManager()
            cm.get_aiproject_client()
            
            # Check if AIProjectClient was initialized with the credential
            assert mock_ai_client_cls.called
            args, kwargs = mock_ai_client_cls.call_args
            assert kwargs["credential"] == mock_cred
            assert kwargs["endpoint"] == "https://test.endpoint"

def test_credential_passthrough_to_aiproject_client_conn_str(monkeypatch):
    """Verify that the credential from ClientManager is passed to AIProjectClient (connection string style)."""
    # Simulate a full connection string
    monkeypatch.setenv("AZURE_AAIF_PROJECT_ENDPOINT", "location=eastus;endpoint=https://ai.example.com;project=foo")
    
    with patch("src.utils.m_ai_client._AuthManager.get_azure_credential") as mock_get_cred:
        mock_cred = MagicMock()
        mock_get_cred.return_value = mock_cred
        
        # Patch AIProjectClient where it is USED in src.utils.m_ai_client
        with patch("src.utils.m_ai_client.projects.AIProjectClient") as mock_ai_client_cls:
            cm = ClientManager()
            cm.get_aiproject_client()
            
            # Check if AIProjectClient was initialized with the PARSED endpoint and credential
            assert mock_ai_client_cls.called
            args, kwargs = mock_ai_client_cls.call_args
            assert kwargs["credential"] == mock_cred
            assert kwargs["endpoint"] == "https://ai.example.com"

def test_orchestrator_agent_credential_sharing():
    """Verify that agents share the same ClientManager and thus the same credential instance."""
    cm = ClientManager()
    reviewer = IntakeReviewerAgent(client_manager=cm)
    composer = ArchitectureComposerAgent(client_manager=cm)
    
    assert reviewer.client_manager == cm
    assert composer.client_manager == cm
    
    cred1 = reviewer.client_manager.get_credential()
    cred2 = composer.client_manager.get_credential()
    assert cred1 == cred2
