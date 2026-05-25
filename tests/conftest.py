import pytest

import src.utils.m_log as m_log


@pytest.fixture(autouse=True)
def neutralize_sp_auth_mode(monkeypatch):
    """Pin auth to the CI default (cli) so tests never depend on the developer's local
    .env. With the SP secret now sourced from Key Vault, .env carries AZURE_AUTH_MODE=sp
    with a blank AZURE_CLIENT_SECRET locally, which would otherwise trip the missing-secret
    guard during credential construction."""
    monkeypatch.setattr("src.config.USE_AZURE_SERVICE_PRINCIPAL", False, raising=False)


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging state between every test to prevent handler accumulation."""
    import logging

    m_log._is_configured = False
    m_log._logger.handlers.clear()
    logging.root.handlers.clear()
    yield
    m_log._is_configured = False
    m_log._logger.handlers.clear()
    logging.root.handlers.clear()


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings for tests — prevents reading .env from disk."""
    monkeypatch.setattr("src.config.settings.log_profile", "TEST")
    monkeypatch.setattr("src.config.settings.google_api_key", "test-key")
