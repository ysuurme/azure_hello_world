from unittest.mock import MagicMock, patch

import pytest

from src.utils.m_health_check import run_health_check


@patch("src.utils.m_health_check.config.AZURE_AAIF_PROJECT_ENDPOINT", "")
def test_run_health_check_no_endpoint():
    """Test that health check exits if endpoint is not set."""
    with pytest.raises(SystemExit) as exc_info:
        run_health_check()
    assert exc_info.value.code == 1


@patch("src.utils.m_health_check.config.AZURE_AAIF_PROJECT_ENDPOINT", "https://fake.endpoint")
@patch("src.utils.m_health_check.ClientManager")
def test_run_health_check_success_no_deployments(mock_client_manager):
    """Test successful health check when deployment listing is not available."""
    mock_cm = mock_client_manager.return_value
    
    # Mock project client without inference
    mock_project_client = MagicMock()
    del mock_project_client.inference
    mock_cm.get_aiproject_client.return_value = mock_project_client

    # Mock openai client context manager
    mock_openai_client = MagicMock()
    mock_cm.get_openai_client.return_value.__enter__.return_value = mock_openai_client

    # Mock chat completion response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "OK"
    mock_openai_client.chat.completions.create.return_value = mock_response

    try:
        run_health_check()
    except SystemExit:
        pytest.fail("run_health_check exited unexpectedly")


@patch("src.utils.m_health_check.config.AZURE_AAIF_PROJECT_ENDPOINT", "https://fake.endpoint")
@patch("src.utils.m_health_check.ClientManager")
@patch("src.utils.m_health_check.config.AGENT_MODELS", {"intake_reviewer": "gpt-4o"})
def test_run_health_check_success_with_deployments(mock_client_manager):
    """Test successful health check with deployment listing."""
    mock_cm = mock_client_manager.return_value
    
    # Mock project client with inference and deployments
    mock_project_client = MagicMock()
    mock_deployment = MagicMock()
    mock_deployment.name = "gpt-4o"
    mock_project_client.inference.get_deployments.return_value = [mock_deployment]
    mock_cm.get_aiproject_client.return_value = mock_project_client

    # Mock openai client context manager
    mock_openai_client = MagicMock()
    mock_cm.get_openai_client.return_value.__enter__.return_value = mock_openai_client

    # Mock chat completion response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "OK"
    mock_openai_client.chat.completions.create.return_value = mock_response

    try:
        run_health_check()
    except SystemExit:
        pytest.fail("run_health_check exited unexpectedly")


@patch("src.utils.m_health_check.config.AZURE_AAIF_PROJECT_ENDPOINT", "https://fake.endpoint")
@patch("src.utils.m_health_check.ClientManager")
def test_run_health_check_empty_response(mock_client_manager):
    """Test health check exits when receiving empty response."""
    mock_cm = mock_client_manager.return_value
    mock_project_client = MagicMock()
    mock_cm.get_aiproject_client.return_value = mock_project_client

    mock_openai_client = MagicMock()
    mock_cm.get_openai_client.return_value.__enter__.return_value = mock_openai_client

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "   " # Empty stripped
    mock_openai_client.chat.completions.create.return_value = mock_response

    with pytest.raises(SystemExit) as exc_info:
        run_health_check()
    assert exc_info.value.code == 1


@patch("src.utils.m_health_check.config.AZURE_AAIF_PROJECT_ENDPOINT", "https://fake.endpoint")
@patch("src.utils.m_health_check.ClientManager")
def test_run_health_check_fallback_max_tokens(mock_client_manager):
    """Test health check fallbacks to max_tokens when max_completion_tokens fails."""
    mock_cm = mock_client_manager.return_value
    mock_project_client = MagicMock()
    mock_cm.get_aiproject_client.return_value = mock_project_client

    mock_openai_client = MagicMock()
    mock_cm.get_openai_client.return_value.__enter__.return_value = mock_openai_client

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "OK"
    
    # First call raises exception with max_completion_tokens
    def mock_create(*args, **kwargs):
        if "max_completion_tokens" in kwargs:
            raise Exception("max_completion_tokens not supported")
        return mock_response

    mock_openai_client.chat.completions.create.side_effect = mock_create

    try:
        run_health_check()
    except SystemExit:
        pytest.fail("run_health_check exited unexpectedly")


@patch("src.utils.m_health_check.config.AZURE_AAIF_PROJECT_ENDPOINT", "https://fake.endpoint")
@patch("src.utils.m_health_check.ClientManager")
def test_run_health_check_exception(mock_client_manager):
    """Test health check handles and logs unexpected exceptions."""
    mock_cm = mock_client_manager.return_value
    mock_cm.get_aiproject_client.side_effect = Exception("DeploymentNotFound 404")

    with pytest.raises(SystemExit) as exc_info:
        run_health_check()
    assert exc_info.value.code == 1
